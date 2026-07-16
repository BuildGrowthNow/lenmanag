from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

import boto3
from botocore.config import Config as BotoConfig
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """Wrapper around Amazon Bedrock for text and vision analysis with fallback models."""

    def __init__(self):
        settings = get_settings()
        self.model_id = settings.bedrock_model_id
        self.region = settings.bedrock_region
        self.max_tokens = settings.bedrock_max_tokens
        self.timeout_seconds = settings.bedrock_timeout_seconds
        self.fallback_models = settings.bedrock_fallback_models
        self.consecutive_timeouts = 0

        boto_config = BotoConfig(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=self.timeout_seconds,
            read_timeout=self.timeout_seconds,
        )
        self.client = boto3.client("bedrock-runtime", config=boto_config)

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text response from Bedrock with automatic fallback to alternate models."""
        model_to_try = self.model_id
        models_to_try = [self.model_id] + self.fallback_models

        for i, model_to_try in enumerate(models_to_try):
            try:
                return await self._invoke_bedrock(
                    model_id=model_to_try,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except (TimeoutError, Exception) as e:
                error_str = str(e)
                is_timeout = (
                    "timeout" in error_str.lower() or
                    "read timeout" in error_str.lower() or
                    isinstance(e, TimeoutError)
                )

                if is_timeout:
                    self.consecutive_timeouts += 1
                else:
                    self.consecutive_timeouts = 0

                logger.warning(
                    f"Bedrock generation failed with model {model_to_try} "
                    f"(timeout={is_timeout}, attempt={i+1}/{len(models_to_try)}): {e}"
                )

                # If this was the last model, raise the error
                if i == len(models_to_try) - 1:
                    logger.error(
                        f"All Bedrock models exhausted. Last error: {e}"
                    )
                    raise ValueError(f"Bedrock text generation failed after all fallbacks: {e}")

        # Should never reach here, but satisfy type checker
        raise ValueError("Bedrock text generation failed: no models to try")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=5))
    async def _invoke_bedrock(
        self,
        model_id: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Internal method to invoke Bedrock with a specific model."""
        try:
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            text = result["content"][0]["text"]
            if not text:
                raise ValueError("Empty response from Bedrock")
            # Reset timeout counter on success
            self.consecutive_timeouts = 0
            return text
        except Exception as e:
            logger.error(f"Bedrock invocation failed for model {model_id}: {e}")
            raise

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

        for i, model_to_try in enumerate(models_to_try):
            try:
                return await self._invoke_bedrock_vision(
                    model_id=model_to_try,
                    prompt=prompt,
                    image_data=image_data,
                    image_mime_type=image_mime_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except (TimeoutError, Exception) as e:
                if i == len(models_to_try) - 1:
                    logger.error(
                        f"All Bedrock models exhausted for vision analysis. Last error: {e}"
                    )
                    raise ValueError(f"Bedrock vision analysis failed after all fallbacks: {e}")
                logger.warning(
                    f"Vision analysis failed with model {model_to_try}, trying next: {e}"
                )

        # Should never reach here, but satisfy type checker
        raise ValueError("Bedrock vision analysis failed: no models to try")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=5))
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
        try:
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
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            text = result["content"][0]["text"]
            if not text:
                raise ValueError("Empty response from Bedrock Vision")
            self.consecutive_timeouts = 0
            return text
        except Exception as e:
            logger.error(f"Bedrock vision invocation failed for model {model_id}: {e}")
            raise

    async def batch_generate_text(
        self,
        prompts: list[str],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> list[str]:
        """Generate multiple text responses in parallel."""
        import asyncio

        tasks = [
            self.generate_text(prompt, temperature, max_tokens) for prompt in prompts
        ]
        return await asyncio.gather(*tasks)

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
            logger.error(f"Failed to parse JSON from response: {response}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")


_bedrock_client: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """Get or create Bedrock client."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client
