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
    """Wrapper around Amazon Bedrock for text and vision analysis."""

    def __init__(self):
        settings = get_settings()
        self.model_id = settings.bedrock_model_id
        self.region = settings.bedrock_region
        self.max_tokens = settings.bedrock_max_tokens

        boto_config = BotoConfig(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self.client = boto3.client("bedrock-runtime", config=boto_config)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text response from Bedrock Claude."""
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            })
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            text = result["content"][0]["text"]
            if not text:
                raise ValueError("Empty response from Bedrock")
            return text
        except Exception as e:
            logger.error(f"Bedrock text generation failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def analyze_image(
        self,
        prompt: str,
        image_data: bytes,
        image_mime_type: str = "image/png",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Analyze image with Bedrock Claude Vision."""
        try:
            encoded = base64.b64encode(image_data).decode()
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{
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
                }],
            })
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            text = result["content"][0]["text"]
            if not text:
                raise ValueError("Empty response from Bedrock Vision")
            return text
        except Exception as e:
            logger.error(f"Bedrock vision analysis failed: {e}")
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
            self.generate_text(prompt, temperature, max_tokens)
            for prompt in prompts
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
            f"Operator refinement request:\n\"{operator_prompt}\"\n\n"
            "Produce a JSON object with refined guidance for visual redesign:\n"
            "{\n"
            "  \"refinedFocus\": \"Updated design direction\",\n"
            "  \"sectionOrder\": [\"section1\", \"section2\", ...],\n"
            "  \"componentSuggestions\": [\n"
            "    {\"section\": \"Hero\", \"suggestedComponent\": \"hero-split-editorial\"}\n"
            "  ],\n"
            "  \"ctaStrategy\": \"Refined CTA approach\",\n"
            "  \"visualTone\": \"Updated visual tone\",\n"
            "  \"additionalNotes\": \"Implementation hints\"\n"
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
