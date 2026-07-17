from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Optional

import boto3
from botocore.config import Config as BotoConfig
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FAST_TIMEOUT_SECONDS = 60
"""Per-model timeout before falling back to the next model in the chain."""


class BedrockClient:
    """Wrapper around Amazon Bedrock for text and vision analysis with fallback models."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model_id = settings.bedrock_model_id
        self.region = settings.bedrock_region
        self.max_tokens = settings.bedrock_max_tokens
        self.timeout_seconds = settings.bedrock_timeout_seconds
        self.fallback_models = settings.bedrock_fallback_models
        self._model_failures: dict[str, int] = {}

        self._clients: dict[str, Any] = {}
        self._clients[self.region] = self._create_client(self.region)

    def _create_client(self, region: str) -> Any:
        boto_config = BotoConfig(
            region_name=region,
            retries={"max_attempts": 2, "mode": "adaptive"},
            connect_timeout=30,
            read_timeout=self.timeout_seconds,
        )
        return boto3.client("bedrock-runtime", config=boto_config)

    def _get_client_for_model(self, model_id: str) -> Any:  # noqa: ARG002
        """Get a boto3 client appropriate for the model (handles cross-region)."""
        return self._clients[self.region]

    def _should_skip_model(self, model_id: str) -> bool:
        """Skip models that have failed 3+ consecutive times recently."""
        return self._model_failures.get(model_id, 0) >= 3

    def _record_failure(self, model_id: str) -> None:
        self._model_failures[model_id] = self._model_failures.get(model_id, 0) + 1

    def _record_success(self, model_id: str) -> None:
        self._model_failures.pop(model_id, None)

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text response from Bedrock with automatic fallback to alternate models."""
        models_to_try = [self.model_id] + self.fallback_models
        models_to_try = [m for m in models_to_try if not self._should_skip_model(m)]

        if not models_to_try:
            self._model_failures.clear()
            models_to_try = [self.model_id] + self.fallback_models

        last_error: Exception | None = None
        for i, model_to_try in enumerate(models_to_try):
            start = time.monotonic()
            try:
                result = await self._invoke_bedrock(
                    model_id=model_to_try,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed = time.monotonic() - start
                logger.info(
                    "Bedrock generation succeeded with %s in %.1fs",
                    model_to_try,
                    elapsed,
                )
                self._record_success(model_to_try)
                return result
            except Exception as e:
                last_error = e
                elapsed = time.monotonic() - start
                error_str = str(e).lower()
                is_timeout = "timeout" in error_str or "read timeout" in error_str

                logger.warning(
                    "Bedrock model %s failed (timeout=%s, %.1fs, attempt %d/%d): %s",
                    model_to_try,
                    is_timeout,
                    elapsed,
                    i + 1,
                    len(models_to_try),
                    e,
                )
                self._record_failure(model_to_try)

        raise ValueError(
            f"Bedrock text generation failed after all fallbacks: {last_error}"
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
    async def _invoke_bedrock(
        self,
        model_id: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Internal method to invoke Bedrock with a specific model."""
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        client = self._get_client_for_model(model_id)
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        if not text:
            raise ValueError("Empty response from Bedrock")
        return text

    async def analyze_image(
        self,
        prompt: str,
        image_data: bytes,
        image_mime_type: str = "image/png",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Analyze image with Bedrock Claude Vision with fallback models."""
        models_to_try = [self.model_id] + self.fallback_models
        models_to_try = [m for m in models_to_try if not self._should_skip_model(m)]

        if not models_to_try:
            self._model_failures.clear()
            models_to_try = [self.model_id] + self.fallback_models

        last_error: Exception | None = None
        for i, model_to_try in enumerate(models_to_try):
            try:
                result = await self._invoke_bedrock_vision(
                    model_id=model_to_try,
                    prompt=prompt,
                    image_data=image_data,
                    image_mime_type=image_mime_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._record_success(model_to_try)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "Vision analysis failed with model %s (attempt %d/%d): %s",
                    model_to_try,
                    i + 1,
                    len(models_to_try),
                    e,
                )
                self._record_failure(model_to_try)

        raise ValueError(
            f"Bedrock vision analysis failed after all fallbacks: {last_error}"
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
    async def _invoke_bedrock_vision(
        self,
        model_id: str,
        prompt: str,
        image_data: bytes,
        image_mime_type: str = "image/png",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Internal method to invoke Bedrock vision with a specific model."""
        encoded = base64.b64encode(image_data).decode()
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_mime_type,
                                    "data": encoded,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            }
        )
        client = self._get_client_for_model(model_id)
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        if not text:
            raise ValueError("Empty response from Bedrock Vision")
        return text

    async def batch_generate_text(
        self,
        prompts: list[str],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> list[str]:
        """Generate multiple text responses sequentially (avoids rate limiting)."""
        results: list[str] = []
        for prompt in prompts:
            result = await self.generate_text(prompt, temperature, max_tokens)
            results.append(result)
        return results

    async def refine_brief_with_operator_prompt(
        self,
        extraction_summary: str,
        current_brief_summary: str,
        brand_tokens_summary: str,
        operator_prompt: str,
    ) -> dict[str, Any]:
        """Use operator natural-language prompt to refine visual redesign brief."""

        prompt = (
            "You are a design brief refinement assistant. An operator has provided "
            "refinement guidance on an existing website redesign. Your job is to "
            "synthesize their request with the current brief.\n\n"
            f"Current brief summary:\n{current_brief_summary}\n\n"
            f"Brand tokens:\n{brand_tokens_summary}\n\n"
            f"Original extraction:\n{extraction_summary}\n\n"
            f'Operator refinement request:\n"{operator_prompt}"\n\n'
            "Produce a JSON object with refined guidance for visual redesign:\n"
            "{\n"
            '  "refinedFocus": "Updated design direction",\n'
            '  "sectionOrder": ["section1", "section2", ...],\n'
            '  "componentSuggestions": [\n'
            '    {"section": "Hero", "suggestedComponent": "hero-split-editorial"}\n'
            "  ],\n"
            '  "ctaStrategy": "Refined CTA approach",\n'
            '  "visualTone": "Updated visual tone",\n'
            '  "additionalNotes": "Implementation hints"\n'
            "}\n\n"
            "CONSTRAINTS:\n"
            "- Do NOT rewrite extracted product facts or content\n"
            "- Do NOT invent testimonials, pricing, or claims not in source\n"
            "- Do NOT change brand colors or visual tokens\n"
            "- Do NOT suggest components that don't exist\n"
            "- Keep changes grounded in the operator's guidance and extraction data\n\n"
            "Only return valid JSON, no additional text."
        )

        response = await self.generate_text(prompt, temperature=0.6, max_tokens=1500)
        return self.extract_json_from_response(response)

    def extract_json_from_response(self, response: str) -> dict[str, Any]:
        """Extract JSON from response (handles markdown code blocks)."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {response[:500]}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")


_bedrock_client: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """Get or create Bedrock client."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client
