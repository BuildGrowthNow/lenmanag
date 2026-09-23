from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.bedrock_client import BedrockClient
from app.core.config import Settings


def _settings(**overrides: object) -> SimpleNamespace:
    values = {
        "bedrock_model_id": "global.anthropic.claude-sonnet-4-6",
        "bedrock_region": "us-east-1",
        "bedrock_max_tokens": 32768,
        "bedrock_timeout_seconds": 600,
        "bedrock_fallback_model_list": [
            "amazon.nova-pro-v1:0",
            "mistral.mistral-large-2402-v1:0",
        ],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _response(text: str) -> dict[str, object]:
    return {"output": {"message": {"content": [{"text": text}]}}}


@pytest.mark.asyncio
async def test_text_generation_uses_converse_and_falls_back_across_models() -> None:
    bedrock_runtime = MagicMock()
    bedrock_runtime.converse.side_effect = [
        ValueError("primary unavailable"),
        _response("fallback output"),
    ]

    with (
        patch("app.core.bedrock_client.get_settings", return_value=_settings()),
        patch("app.core.bedrock_client.boto3.client", return_value=bedrock_runtime),
    ):
        client = BedrockClient()
        result = await client.generate_text("Build a site", max_tokens=1234)

    assert result == "fallback output"
    assert [call.kwargs["modelId"] for call in bedrock_runtime.converse.call_args_list] == [
        "global.anthropic.claude-sonnet-4-6",
        "amazon.nova-pro-v1:0",
    ]
    request = bedrock_runtime.converse.call_args_list[0].kwargs
    assert request["messages"] == [
        {"role": "user", "content": [{"text": "Build a site"}]}
    ]
    assert request["inferenceConfig"] == {"maxTokens": 1234, "temperature": 0.7}


@pytest.mark.asyncio
async def test_vision_generation_uses_bedrock_image_content() -> None:
    bedrock_runtime = MagicMock()
    bedrock_runtime.converse.return_value = _response("visual QA")

    with (
        patch("app.core.bedrock_client.get_settings", return_value=_settings()),
        patch("app.core.bedrock_client.boto3.client", return_value=bedrock_runtime),
    ):
        client = BedrockClient()
        result = await client.analyze_image(
            "Inspect this", b"png-bytes", image_mime_type="image/png"
        )

    assert result == "visual QA"
    request = bedrock_runtime.converse.call_args.kwargs
    assert request["messages"][0]["content"] == [
        {"image": {"format": "png", "source": {"bytes": b"png-bytes"}}},
        {"text": "Inspect this"},
    ]


def test_bedrock_fallback_setting_accepts_comma_separated_and_json_values() -> None:
    comma_settings = Settings(
        _env_file=None,
        bedrock_fallback_models="model-a, model-b,model-a",
    )
    json_settings = Settings(
        _env_file=None,
        bedrock_fallback_models='["model-a", "model-b"]',
    )

    assert comma_settings.bedrock_fallback_model_list == ["model-a", "model-b"]
    assert json_settings.bedrock_fallback_model_list == ["model-a", "model-b"]
