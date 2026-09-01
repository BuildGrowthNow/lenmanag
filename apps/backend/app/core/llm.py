"""LLM provider abstraction."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048
    ) -> str: ...
    async def analyze_image(
        self,
        prompt: str,
        image_data: bytes,
        image_mime_type: str = "image/png",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str: ...
    async def batch_generate_text(
        self, prompts: list[str], temperature: float = 0.7, max_tokens: int = 2048
    ) -> list[str]: ...
    async def refine_brief_with_operator_prompt(
        self,
        extraction_summary: str,
        current_brief_summary: str,
        brand_tokens_summary: str,
        operator_prompt: str,
    ) -> dict[str, Any]: ...
    def extract_json_from_response(self, response: str) -> dict[str, Any]: ...


def get_llm_client() -> LLMClient:
    """Return the LLM client based on LLM_PROVIDER setting."""
    from app.core.config import get_settings

    settings = get_settings()
    provider = (settings.llm_provider or "gemini").lower()

    if provider == "cloudflare":
        from app.core.cloudflare_client import get_cloudflare_client

        return get_cloudflare_client()
    if provider == "bedrock":
        from app.core.bedrock_client import get_bedrock_client

        return get_bedrock_client()
    else:
        from app.core.gemini_client import get_gemini_client

        return get_gemini_client()
