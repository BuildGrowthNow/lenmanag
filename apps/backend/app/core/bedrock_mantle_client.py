"""Small Amazon Bedrock Mantle Chat Completions client for LLM fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BedrockMantleClient:
    """Invoke a configured Mantle model using the instance's AWS credentials."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model_id = settings.bedrock_mantle_model_id
        self.region = settings.bedrock_mantle_region
        self.timeout_seconds = settings.bedrock_mantle_timeout_seconds
        self._session = boto3.Session(region_name=self.region)

    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048
    ) -> str:
        url = f"https://bedrock-mantle.{self.region}.api.aws/v1/chat/completions"
        body = json.dumps(
            {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": min(max_tokens, 16_000),
            }
        ).encode()
        credentials = self._session.get_credentials()
        if credentials is None:
            raise ValueError("AWS credentials not configured for Bedrock Mantle")

        request = AWSRequest(
            method="POST", url=url, data=body, headers={"Content-Type": "application/json"}
        )
        SigV4Auth(
            credentials.get_frozen_credentials(), "bedrock-mantle", self.region
        ).add_auth(request)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, content=body, headers=dict(request.headers))
        if response.is_error:
            raise RuntimeError(
                f"Bedrock Mantle HTTP {response.status_code}: {response.text[:1000]}"
            )
        try:
            payload: dict[str, Any] = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("Bedrock Mantle returned no text") from exc
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Bedrock Mantle returned empty text")
        logger.info("Bedrock Mantle generation succeeded with %s", self.model_id)
        return content


_bedrock_mantle_client: BedrockMantleClient | None = None


def get_bedrock_mantle_client() -> BedrockMantleClient:
    global _bedrock_mantle_client
    if _bedrock_mantle_client is None:
        _bedrock_mantle_client = BedrockMantleClient()
    return _bedrock_mantle_client
