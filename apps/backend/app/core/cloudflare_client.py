"""Cloudflare Workers AI client with ordered model fallbacks."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CloudflareClient:
    """Call Workers AI through Cloudflare's OpenAI-compatible REST API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.cloudflare_account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID not configured")
        if not settings.cloudflare_api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN not configured")
        self.account_id = settings.cloudflare_account_id
        self.api_token = settings.cloudflare_api_token
        self.models = [settings.cloudflare_model] + settings.cloudflare_fallback_model_list
        self.vision_model = settings.cloudflare_vision_model
        self.timeout_seconds = settings.cloudflare_timeout_seconds
        self._model_failures: dict[str, int] = {}

    def _chat_url(self) -> str:
        return f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/v1/chat/completions"

    def _run_url(self, model: str) -> str:
        return f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model}"

    def _should_skip(self, model: str) -> bool:
        return self._model_failures.get(model, 0) >= 3

    def _record_failure(self, model: str) -> None:
        self._model_failures[model] = self._model_failures.get(model, 0) + 1

    def _record_success(self, model: str) -> None:
        self._model_failures.pop(model, None)

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        result = payload.get("result", payload)
        if isinstance(result, dict):
            choices = result.get("choices")
            if choices and isinstance(choices[0], dict):
                message = choices[0].get("message", {})
                content = message.get("content") if isinstance(message, dict) else None
                if isinstance(content, str) and content.strip():
                    return content
                text = choices[0].get("text")
                if isinstance(text, str) and text.strip():
                    return text
            response = result.get("response")
            if isinstance(response, str) and response.strip():
                return response
        raise ValueError("Cloudflare Workers AI returned no text")

    async def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=body)
        try:
            payload = response.json()
        except ValueError:
            payload = {"error": response.text[:500]}
        if response.is_error:
            raise RuntimeError(f"Cloudflare Workers AI HTTP {response.status_code}: {json.dumps(payload)[:1000]}")
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(f"Cloudflare Workers AI error: {json.dumps(payload)[:1000]}")
        return payload

    async def generate_text(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        models = [model for model in self.models if not self._should_skip(model)]
        if not models:
            self._model_failures.clear()
            models = self.models
        last_error: Exception | None = None
        for model in models:
            try:
                payload = await self._post(self._chat_url(), {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    # DeepSeek Flash otherwise spends the completion budget on
                    # hidden reasoning and can finish with content=null. These
                    # calls need a complete artifact, not a chain of thought.
                    "chat_template_kwargs": {"enable_thinking": False},
                })
                result = self._extract_text(payload)
                self._record_success(model)
                logger.info("Cloudflare Workers AI generation succeeded with %s", model)
                return result
            except Exception as exc:
                last_error = exc
                self._record_failure(model)
                logger.warning("Cloudflare model %s failed: %s", model, exc)
        try:
            from app.core.bedrock_mantle_client import get_bedrock_mantle_client

            result = await get_bedrock_mantle_client().generate_text(
                prompt, temperature, max_tokens
            )
            logger.info("Cloudflare fallback succeeded with Bedrock Mantle")
            return result
        except Exception as exc:
            logger.warning("Bedrock Mantle fallback failed: %s", exc)
        raise ValueError(f"Cloudflare Workers AI failed after all fallbacks: {last_error}")

    async def analyze_image(self, prompt: str, image_data: bytes, image_mime_type: str = "image/png", temperature: float = 0.7, max_tokens: int = 2048) -> str:
        image = f"data:{image_mime_type};base64,{base64.b64encode(image_data).decode()}"
        if self.vision_model in {"@cf/qwen/qwen3.8-27b", "@cf/zai-org/glm-5.3-flash"}:
            payload = await self._post(self._chat_url(), {
                "model": self.vision_model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image}},
                    ],
                }],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "chat_template_kwargs": {"enable_thinking": False},
            })
        else:
            payload = await self._post(self._run_url(self.vision_model), {
                "prompt": prompt, "image": image, "temperature": temperature, "max_tokens": max_tokens,
            })
        return self._extract_text(payload)

    async def batch_generate_text(self, prompts: list[str], temperature: float = 0.7, max_tokens: int = 2048) -> list[str]:
        return [await self.generate_text(prompt, temperature, max_tokens) for prompt in prompts]

    async def refine_brief_with_operator_prompt(self, extraction_summary: str, current_brief_summary: str, brand_tokens_summary: str, operator_prompt: str) -> dict[str, Any]:
        prompt = (
            "You are a design brief refinement assistant. Synthesize the operator request with the current brief and return only valid JSON.\n\n"
            f"Current brief summary:\n{current_brief_summary}\n\nBrand tokens:\n{brand_tokens_summary}\n\n"
            f"Original extraction:\n{extraction_summary}\n\nOperator refinement request:\n{operator_prompt}\n\n"
            "Return an object with keys: refinedFocus, sectionOrder, componentSuggestions, ctaStrategy, visualTone, additionalNotes. "
            "Do not invent facts, claims, pricing, testimonials, colors, or components."
        )
        return self.extract_json_from_response(await self.generate_text(prompt, temperature=0.6, max_tokens=1500))

    def extract_json_from_response(self, response: str) -> dict[str, Any]:
        cleaned = response.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end + 1])
            raise ValueError("Invalid JSON in Cloudflare Workers AI response")


_cloudflare_client: Optional[CloudflareClient] = None


def get_cloudflare_client() -> CloudflareClient:
    global _cloudflare_client
    if _cloudflare_client is None:
        _cloudflare_client = CloudflareClient()
    return _cloudflare_client
