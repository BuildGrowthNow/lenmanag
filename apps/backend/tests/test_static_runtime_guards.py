from types import SimpleNamespace

import pytest

from app.core.asset_utils import get_best_asset_url
from app.core.site_screenshot import _fatal_runtime_failures
from app.core.static_html_generator import (
    _enforce_footer_year,
    _javascript_is_valid,
    _parse_llm_response,
    _remove_generated_asset_references,
    _validate_generated_document,
    _verified_contact_data,
    _build_static_html_prompt,
    _apply_static_safety_layer,
)
from app.schemas.brief import MasterBrief
from app.schemas.extraction import ExtractionSnapshot
from app.core.extraction import _extract_contact_info
from app.core.sites import is_usable_generated_site
from datetime import datetime, timezone


def test_truncated_javascript_is_rejected() -> None:
    with pytest.raises(ValueError, match="Expected closed"):
        _parse_llm_response("```html\n<!DOCTYPE html><html><head></head><body></body></html>\n```\n```css\na{}\n```\n```javascript\nconst x =")


def test_invalid_javascript_never_validates_for_upload() -> None:
    assert not _javascript_is_valid("document.addEventListener('x', () => {")


def test_relative_generated_asset_references_are_removed() -> None:
    html = '<html><head><link rel="stylesheet" href="/st/demo/styles.css"></head><body><script src="./script.js"></script></body></html>'
    cleaned = _remove_generated_asset_references(html)
    assert "styles.css" not in cleaned and "script.js" not in cleaned


def test_page_url_cannot_become_logo_and_relative_asset_resolves() -> None:
    assert get_best_asset_url({"assetUrl": "https://example.test/", "sourceUrl": "https://example.test/"}) is None
    assert get_best_asset_url({"value": "/assets/brand.svg", "pageUrl": "https://example.test/about"}) == "https://example.test/assets/brand.svg"


def test_fatal_runtime_health_blocks_readiness() -> None:
    failures = _fatal_runtime_failures({"pageErrors": ["SyntaxError"], "readiness": False, "mainContentRendered": True})
    assert "page_errors" in failures and "readiness_missing_or_false" in failures


def test_document_requires_closed_structure() -> None:
    with pytest.raises(ValueError):
        _validate_generated_document("<!DOCTYPE html><html><head></head><body>", "a{}", "const a = 1;")


def _brief_with_logo(logo: str | None):
    return SimpleNamespace(
        brandAssets=SimpleNamespace(
            logoUrl=logo,
            logoLightUrl=None,
            logoDarkUrl=None,
            logoVariants=[],
            imageUrls=[],
        ),
        sections=[],
        contactInfo={},
    )


def _valid_document(logo: str | None = None) -> str:
    logo_markup = f'<img src="{logo}" alt="Logo">' if logo else ""
    return f"<!doctype html><html><head><title>Test</title></head><body><header>{logo_markup}<h1>Service</h1></header><main><p>Content</p></main></body></html>"


def test_exact_header_logo_is_required() -> None:
    logo = "https://cdn.example.test/logo.svg"
    _validate_generated_document(_valid_document(logo), "body { color: black; }", "const ready = true;", _brief_with_logo(logo))


def test_omitted_or_wrong_header_logo_is_rejected() -> None:
    logo = "https://cdn.example.test/logo.svg"
    with pytest.raises(ValueError, match="approved header logo"):
        _validate_generated_document(_valid_document(), "body {}", "const ready = true;", _brief_with_logo(logo))
    with pytest.raises(ValueError, match="approved header logo"):
        _validate_generated_document(_valid_document("https://cdn.example.test/other.svg"), "body {}", "const ready = true;", _brief_with_logo(logo))


def test_no_logo_available_does_not_require_a_logo() -> None:
    _validate_generated_document(_valid_document(), "body {}", "const ready = true;", _brief_with_logo(None))


def test_dark_logo_is_inverted_for_dark_variant() -> None:
    logo = "https://cdn.example.test/logo-dark.svg"
    brief = _brief_with_logo(logo)
    brief.brandAssets.logoDarkUrl = logo
    html, css, _js = _apply_static_safety_layer(_valid_document(logo), "body {}", "const ready = true;", brief, "html_v2")
    assert "lq-logo-light-on-dark" in html
    assert ".lq-logo-light-on-dark { filter: brightness(0) invert(1); }" in css


def test_generated_document_rejects_em_dash_and_prohibited_fonts() -> None:
    with pytest.raises(ValueError, match="em dash"):
        _validate_generated_document(_valid_document().replace("Service", "Service — trusted"), "body {}", "const ready = true;")
    with pytest.raises(ValueError, match="Windows font"):
        _validate_generated_document(_valid_document(), "body { font-family: Arial; }", "const ready = true;")


def test_generated_document_requires_an_approved_image_url() -> None:
    brief = _brief_with_logo(None)
    brief.brandAssets.imageUrls = ["http://cdn.example.test/work.jpg"]
    with pytest.raises(ValueError, match="approved photography"):
        _validate_generated_document(_valid_document(), "body {}", "const ready = true;", brief)
    html = _valid_document().replace("</main>", '<img src="https://cdn.example.test/work.jpg" alt="Work"></main>')
    _validate_generated_document(html, "body {}", "const ready = true;", brief)


def test_static_preview_eligibility_does_not_require_compiled_bundle() -> None:
    site = SimpleNamespace(
        variantType="html_v1", staticHtml=_valid_document(), compilationStatus="success",
        compiledBundleUrl=None, readinessStatus="ready_for_review", previewUrl="https://sites.example/st/demo", previewSlug="demo",
    )
    assert is_usable_generated_site(site)
    site.staticHtml = ""
    assert not is_usable_generated_site(site)


def test_compiled_preview_still_requires_bundle() -> None:
    site = SimpleNamespace(
        variantType="nextjs", staticHtml=None, compilationStatus="success",
        compiledBundleUrl="https://cdn.example/bundle.js", readinessStatus="ready_for_review", previewUrl="https://sites.example/st/demo", previewSlug="demo",
    )
    assert is_usable_generated_site(site)
    site.compiledBundleUrl = None
    assert not is_usable_generated_site(site)


def test_single_pass_prompt_contains_exact_logo_contract() -> None:
    logo = "https://cdn.example.test/logo.svg"
    brief = _brief_with_logo(logo)
    brief.businessGoal = brief.primaryAudience = brief.valueProposition = brief.headline = brief.subheadline = brief.toneAndVoice = brief.ctaStrategy = brief.conversionAction = ""
    extraction = SimpleNamespace(
        summary=SimpleNamespace(companyName="Example"),
        contactInfo=SimpleNamespace(model_dump=lambda **_kwargs: {}),
        extractedImages=[],
    )
    brief.visualStyle = brief.colorStrategy = brief.motionLevel = ""
    brief.creativeDirection = SimpleNamespace(
        designConcept="", heroTreatment="", signatureTechnique="", layoutStrategy="", scrollBehavior="",
        colorMood="", typographyPersonality="", microInteractions=[], inspirationKeywords=[], avoidPatterns=[],
    )
    brief.brandAssets.primaryColor = brief.brandAssets.secondaryColor = brief.brandAssets.fontFamily = brief.brandAssets.fontUrl = None
    brief.brandAssets.imageInventory = []
    context = _build_static_html_prompt(brief, extraction, "html_v1")
    assert f"REQUIRED HEADER LOGO URL: {logo}" in context
    assert "src equals this exact URL" in context


def test_footer_year_is_current_but_historic_year_is_preserved() -> None:
    year = str(datetime.now(timezone.utc).year)
    html = "<p>Since 1989</p><footer>© 2024 Example</footer>"
    result = _enforce_footer_year(html)
    assert "Since 1989" in result and f"© {year}" in result


def test_footer_year_is_injected_when_footer_has_no_copyright() -> None:
    year = str(datetime.now(timezone.utc).year)
    result = _enforce_footer_year("<footer><p>Since 1989</p></footer>", company_name="Champion")
    assert f"© Champion {year}" in result and "Since 1989" in result


def test_generation_contact_context_falls_back_to_structured_extraction() -> None:
    brief = MasterBrief.model_construct(contactInfo={})
    extraction = ExtractionSnapshot.model_construct(contactInfo={
        "officePhone": "+1 574-862-4253", "emergencyPhone": "+1 574-849-6188",
        "contactUrl": "https://champion.example/contact", "confidence": 90,
    })
    contacts = _verified_contact_data(brief, extraction)
    assert contacts["officePhone"].endswith("4253")
    assert contacts["emergencyPhone"].endswith("6188")


def test_extracted_contact_info_keeps_real_office_and_emergency_numbers() -> None:
    contacts = _extract_contact_info([{"url": "https://example.test/contact", "cleanedText": "Emergency +1 574-849-6188 Office +1 574-862-4253"}])
    assert contacts["emergencyPhone"].endswith("6188")
    assert contacts["officePhone"].endswith("4253")
