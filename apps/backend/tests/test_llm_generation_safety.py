from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cloudflare_client import CloudflareClient
from app.core.static_html_generator import _generate_split_assets, generate_static_html


def test_cloudflare_empty_or_null_content_is_rejected() -> None:
    for payload in (
        {"result": {"choices": [{"message": {"content": None}}]}},
        {"result": {"choices": [{"message": {"content": "   "}}]}},
        {"result": {"choices": [{"message": {}}]}},
    ):
        with pytest.raises(ValueError, match="returned no text"):
            CloudflareClient._extract_text(payload)


@pytest.mark.asyncio
async def test_cloudflare_disables_reasoning_for_artifact_output() -> None:
    client = CloudflareClient.__new__(CloudflareClient)
    client.models = ["@cf/deepseek-ai/deepseek-v4-flash-0731"]
    client._model_failures = {}
    client._post = AsyncMock(
        return_value={"choices": [{"message": {"content": "artifact"}}]}
    )
    client._chat_url = MagicMock(return_value="https://example.test/chat")

    assert await client.generate_text("make an artifact") == "artifact"
    assert client._post.await_args.args[1]["chat_template_kwargs"] == {
        "enable_thinking": False
    }


@pytest.mark.asyncio
async def test_split_generation_uses_three_bounded_calls() -> None:
    llm = MagicMock()
    llm.generate_text = AsyncMock(
        side_effect=[
            "```html\n<!doctype html><html><head></head><body><main></main></body></html>\n```",
            "```css\nbody { color: black; }\n```",
            "```javascript\nwindow.__LENMANAG_RUNTIME__?.markInitialized?.();\n```",
        ]
    )
    brief = MagicMock()
    brief.sections = []
    extraction = MagicMock()
    extraction.extractedImages = []

    html, css, js = await _generate_split_assets(llm, brief, extraction, "html_v1")

    assert "<html>" in html and "color" in css and "markInitialized" in js
    assert llm.generate_text.await_count == 3
    assert [call.kwargs["max_tokens"] for call in llm.generate_text.await_args_list] == [16_000, 12_000, 8_000]
    assert sum(call.kwargs["max_tokens"] for call in llm.generate_text.await_args_list) == 36_000


@pytest.mark.asyncio
async def test_generation_failure_never_returns_a_fallback_site() -> None:
    failing_llm = MagicMock()
    failing_llm.generate_text = AsyncMock(side_effect=RuntimeError("provider unavailable"))

    with patch("app.core.static_html_generator.get_llm_client", return_value=failing_llm):
        with pytest.raises(ValueError, match="generation failed before publication"):
            await generate_static_html(
                master_brief=MagicMock(),
                extraction=MagicMock(),
                variant_type="html_v1",
                site_id="site-1",
            )
