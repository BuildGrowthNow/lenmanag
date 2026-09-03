from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cloudflare_client import CloudflareClient
from types import SimpleNamespace

from app.core.ai_site_generation import _build_generation_prompt
from app.core.static_html_generator import _build_static_html_prompt, generate_static_html


def test_cloudflare_empty_or_null_content_is_rejected() -> None:
    for payload in (
        {"result": {"choices": [{"message": {"content": None}}]}},
        {"result": {"choices": [{"message": {"content": "   "}}]}},
        {"result": {"choices": [{"message": {}}]}},
    ):
        with pytest.raises(ValueError, match="returned no text"):
            CloudflareClient._extract_text(payload)


def test_cloudflare_text_completion_shape_is_supported() -> None:
    payload = {"result": {"choices": [{"text": "A visual description"}]}}

    assert CloudflareClient._extract_text(payload) == "A visual description"


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
async def test_cloudflare_vision_uses_multimodal_chat_for_verified_models() -> None:
    client = CloudflareClient.__new__(CloudflareClient)
    client.vision_model = "@cf/qwen/qwen3.8-27b"
    client._post = AsyncMock(
        return_value={"choices": [{"message": {"content": "visual QA"}}]}
    )
    client._chat_url = MagicMock(return_value="https://example.test/chat")
    client._run_url = MagicMock(return_value="https://example.test/run")

    assert await client.analyze_image("Inspect this", b"png") == "visual QA"
    url, body = client._post.await_args.args
    assert url == "https://example.test/chat"
    assert body["model"] == "@cf/qwen/qwen3.8-27b"
    assert body["messages"][0]["content"][1]["type"] == "image_url"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    client._run_url.assert_not_called()


@pytest.mark.asyncio
def _brief() -> SimpleNamespace:
    return SimpleNamespace(
        businessGoal="Book qualified service calls", primaryAudience="Homeowners",
        valueProposition="Reliable local service", toneAndVoice="Clear and assured",
        visualStyle="Editorial", colorStrategy="Warm neutrals with a bold accent",
        motionLevel="moderate", headline="Service, made certain", subheadline="Source-backed help.",
        ctaStrategy="Call today", conversionAction="Call today", contactInfo={},
        sections=[SimpleNamespace(purpose="services", headline="What we do", contentSummary="Approved services.", contentPoints=["Repair"], suggestedApproach="Editorial columns")],
        creativeDirection=SimpleNamespace(
            designConcept="Tactile field journal", heroTreatment="Layered editorial hero",
            signatureTechnique="Measured editorial reveal", layoutStrategy="Asymmetric columns",
            scrollBehavior="parallax-layers", colorMood="Grounded warmth",
            typographyPersonality="Expressive serif display", microInteractions=["Magnetic CTA"],
            inspirationKeywords=["editorial", "field notes"], avoidPatterns=["generic service grid"],
        ),
        brandAssets=SimpleNamespace(
            logoUrl="https://cdn.test/logo.svg", logoLightUrl=None, logoDarkUrl=None,
            logoVariants=[], primaryColor="#123456", secondaryColor="#fedcba",
            fontFamily="Inter", fontUrl=None, imageInventory=[], imageUrls=[],
        ),
    )


def _extraction() -> SimpleNamespace:
    return SimpleNamespace(
        summary=SimpleNamespace(companyName="Example Service"),
        contactInfo=SimpleNamespace(model_dump=lambda **_kwargs: {"officePhone": "+1 555 123 4567"}),
    )


def _complete_response() -> str:
    return """```html
<!doctype html><html><head><title>Example</title></head><body><header><img src="https://cdn.test/logo.svg" alt="Example Service"></header><main><h1>Service</h1></main><footer>© Example Service 2026</footer></body></html>
```
```css
body { color: #123456; }
```
```javascript
document.addEventListener('DOMContentLoaded', function () { window.__LENMANAG_RUNTIME__?.markInitialized?.(); });
```"""


def test_single_pass_prompt_contains_full_creative_direction() -> None:
    prompt = _build_static_html_prompt(_brief(), _extraction(), "html_v2")

    for value in (
        "Visual Style", "Color Strategy", "Motion Level", "Design Concept", "Hero Treatment",
        "Signature Technique", "Layout Strategy", "Scroll Behavior", "Color Mood", "Typography",
        "Micro-interactions", "Inspiration Keywords", "Avoid Patterns", "Awwwards-quality",
        "generic service grids", "Never\n     invent testimonials", "https://cdn.test/logo.svg",
    ):
        assert value in prompt


def test_nextjs_prompt_omits_unapproved_proof_and_sets_output_budget() -> None:
    brief = _brief()
    brief.extractedContent = {}
    brief.specialEffects = []
    brief.sections.append(
        SimpleNamespace(
            purpose="social-proof",
            headline="What clients say",
            contentSummary="Customer reviews and ratings.",
            contentPoints=["5 stars"],
            suggestedApproach="testimonial cards",
        )
    )

    prompt = _build_generation_prompt(master_brief=brief, extraction=_extraction())

    assert "None approved. Omit testimonials" in prompt
    assert "What clients say" not in prompt
    assert "under 3,500 lines and under 12,000 generated tokens" in prompt
    assert "Trust badges, testimonials, social proof prominent" not in prompt


@pytest.mark.asyncio
async def test_generation_uses_one_coherent_artifact_request() -> None:
    llm = MagicMock()
    llm.generate_text = AsyncMock(return_value=_complete_response())
    settings = SimpleNamespace(asset_s3_bucket=None, asset_s3_prefix="", asset_s3_region="us-east-1")
    brief = _brief()
    extraction = _extraction()

    with (
        patch("app.core.static_html_generator.get_llm_client", return_value=llm),
        patch("app.core.static_html_generator.get_settings", return_value=settings),
        patch("app.core.static_html_generator._build_static_html_prompt", return_value="FULL MASTER BRIEF PROMPT") as build_prompt,
    ):
        result = await generate_static_html(master_brief=brief, extraction=extraction, variant_type="html_v1", site_id="site-1")

    build_prompt.assert_called_once_with(brief, extraction, "html_v1")
    assert llm.generate_text.await_count == 1
    assert llm.generate_text.await_args.kwargs["prompt"] == "FULL MASTER BRIEF PROMPT"
    assert llm.generate_text.await_args.kwargs["max_tokens"] == 16_384
    assert "data-generated-site-css" in result["html"]
    assert "data-generated-site-js" in result["html"]


@pytest.mark.asyncio
async def test_incomplete_single_pass_response_retries_without_split_generation() -> None:
    llm = MagicMock()
    llm.generate_text = AsyncMock(side_effect=["```html\n<!doctype html>", _complete_response()])
    settings = SimpleNamespace(asset_s3_bucket=None, asset_s3_prefix="", asset_s3_region="us-east-1")
    brief = _brief()
    extraction = _extraction()

    with (
        patch("app.core.static_html_generator.get_llm_client", return_value=llm),
        patch("app.core.static_html_generator.get_settings", return_value=settings),
    ):
        result = await generate_static_html(master_brief=brief, extraction=extraction, variant_type="html_v3", site_id="site-3")

    assert result["html"]
    assert llm.generate_text.await_count == 2
    assert "exactly three CLOSED code blocks" in llm.generate_text.await_args_list[1].kwargs["prompt"]


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
