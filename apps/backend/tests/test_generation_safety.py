"""Regression coverage for public previews and source evidence policies."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bs4 import BeautifulSoup

from app.core.generation_policy import (
    apply_brief_policy, enforce_html_testimonials, normalize_color,
    primary_brand_cue, static_safety_css, stylesheet_color_cues,
    validate_testimonial_source,
)
from app.core.static_html_generator import (
    _attach_static_assets, _extract_complete_block, generate_static_html,
)
from app.core.sites import site_repository
from app.schemas.brief import MasterBrief
from app.schemas.extraction import ExtractionSnapshot


def extraction(**overrides):
    now = datetime.now(timezone.utc)
    return ExtractionSnapshot.model_validate({
        "id": "extraction", "leadId": "lead", "version": 1,
        "crawlStatus": "completed", "sitemapStatus": "found",
        "pagesDiscovered": 1, "pagesCrawled": 1,
        "canonicalWebsiteUrl": "https://getitdone.example",
        "summary": {"companyName": "Get It Done Home Improvements", "canonicalWebsiteUrl": "https://getitdone.example"},
        "confidenceScore": 90, "createdAt": now, "updatedAt": now,
        **overrides,
    })


def brief():
    now = datetime.now(timezone.utc)
    return MasterBrief.model_validate({
        "id": "brief", "leadId": "lead", "sourceExtractionId": "extraction",
        "sourceExtractionVersion": 1, "version": 1, "approvalState": "approved",
        "businessGoal": "Get inquiries", "primaryAudience": "Homeowners",
        "conversionAction": "Call", "valueProposition": "Home improvements",
        "toneAndVoice": "Friendly", "visualStyle": "Editorial",
        "colorStrategy": "Blue accents", "motionLevel": "moderate",
        "headline": "Improve your home", "subheadline": "Local service",
        "ctaStrategy": "Call for an estimate", "confidenceScore": 90,
        "aiReasoning": "Source materials", "createdAt": now, "updatedAt": now,
        "brandAssets": {"primaryColor": "#00f"},
        "sections": [{"purpose": "testimonials", "headline": "Customer reviews",
                      "contentSummary": "Quotes", "suggestedApproach": "Carousel"},
                     {"purpose": "services", "headline": "Our services",
                      "contentSummary": "Home improvements", "suggestedApproach": "Grid"}],
    })


def red_extraction():
    return extraction(brandAssetCues=[
        {"assetType": "color", "label": "Theme color", "value": "#fff",
         "confidence": 99, "sourceUrl": "https://getitdone.example"},
        {"assetType": "color", "label": "Primary brand color", "value": "#c33",
         "confidence": 90, "sourceUrl": "https://getitdone.example/style.css"},
    ])


@pytest.mark.parametrize("value,expected", [("#c33", "#cc3333"), ("#CC3333", "#cc3333"),
                                              ("rgb(204, 51, 51)", "#cc3333"), ("rgb(300,0,0)", None)])
def test_normalize_color(value, expected):
    assert normalize_color(value) == expected


def test_brand_color_wins_over_variant_palette_and_testimonials_are_removed():
    original = brief()
    result = apply_brief_policy(original, red_extraction())
    assert result.brandAssets.primaryColor == "#cc3333"
    assert "cannot replace" in result.colorStrategy
    assert [section.purpose for section in result.sections] == ["services"]
    assert original.brandAssets.primaryColor == "#00f"
    assert apply_brief_policy(result, red_extraction()).colorStrategy == result.colorStrategy
    assert primary_brand_cue(red_extraction()).value == "#c33"


def test_stylesheet_discovers_principal_color_and_preserves_neutral_brand():
    cues = stylesheet_color_cues("body{color:#333;background:#fff} a,.btn{background:#c33} .ornament{color:#00f}", "https://example.com/main.css")
    assert cues[0]["value"] == "#cc3333"
    black = extraction(brandAssetCues=stylesheet_color_cues(":root{--brand-primary:#000;--accent:#f00}", "https://example.com/main.css"))
    assert primary_brand_cue(black).value == "#000000"


@pytest.mark.parametrize("name,url,expected", [
    ("Get It Done Home Improvements", None, "getitdo-v4"),
    ("Green Leaf", None, "green-v4"), (None, "https://www.acmehomes.com", "acmehom-v4"),
    ("AC", None, "acsite-v4"), ("Éclaire", None, "eclaire-v4"),
])
def test_brand_slugs(name, url, expected):
    assert site_repository._generate_variant_slug("uuid", "html_v2", name, website_url=url, variant_number=4) == expected


def test_fake_review_regions_and_rating_schema_are_removed():
    html = '<html><body><section id="services"><h2>Services</h2></section><section class="reviews"><h2>Reviews</h2><p>Made up quote</p></section><div><blockquote>Another invented quote</blockquote></div><script type="application/ld+json">{"@type":"AggregateRating","ratingValue":5}</script></body></html>'
    output = enforce_html_testimonials(html, extraction())
    assert "Made up" not in output and "invented" not in output
    assert "AggregateRating" not in output
    assert 'id="services"' in output


def test_testimonials_are_rebuilt_from_exact_source_records_only():
    evidence = extraction(extractedTestimonials=[{"quote": "Good work & on time", "authorName": "Actual customer", "sourceUrl": "https://getitdone.example/reviews"}])
    output = enforce_html_testimonials('<html><body><section id="testimonials"><p>Fabricated quote</p></section><footer>Contact</footer></body></html>', evidence)
    soup = BeautifulSoup(output, "html.parser")
    assert [quote.get_text() for quote in soup.find_all("blockquote")] == ["Good work & on time"]
    assert soup.figcaption.get_text() == "Actual customer"
    assert "Fabricated" not in output
    assert validate_testimonial_source("const testimonials = [{quote:'Fabricated quote'}]", evidence)
    assert validate_testimonial_source("const testimonials = [{quote:'Good work & on time'}]", evidence) == []
    assert validate_testimonial_source("<blockquote>Fake</blockquote>", extraction())


@pytest.mark.parametrize("remote", [True, False])
def test_local_assets_are_rewritten_once_or_inlined(remote):
    html = '<html><head><link href="./styles.css" rel="stylesheet"><link href="/st/styles.css" rel="stylesheet"><link href="https://vendor.example/font.css"></head><body><script src="script.js"></script><script src="/st/script.js"></script></body></html>'
    output = _attach_static_assets(html, css_url="https://assets.example/styles.css" if remote else None,
                                   js_url="https://assets.example/script.js" if remote else None,
                                   css_content="h1{color:red}", js_content="console.log('ready');")
    soup = BeautifulSoup(output, "html.parser")
    assert "vendor.example/font.css" in output
    assert "/st/styles.css" not in output and "/st/script.js" not in output
    assert len(soup.find_all("script")) == 1
    if remote:
        assert len(soup.find_all("link", href="https://assets.example/styles.css")) == 1
    else:
        assert soup.style.get_text().strip() == "h1{color:red}"
        assert soup.script.get_text().strip() == "console.log('ready');"


def test_hero_readability_and_source_color_are_enforced():
    css = static_safety_css(red_extraction())
    assert "--brand-primary: #cc3333 !important" in css
    assert ".headline-word" in css and "clip-path: none !important" in css
    assert "prefers-reduced-motion" in css


def test_truncated_javascript_is_rejected():
    with pytest.raises(ValueError, match="truncated"):
        _extract_complete_block("```javascript\nfunction broken() {", "javascript")


def test_generation_retries_script_and_publishes_only_complete_validated_output():
    llm = Mock(generate_text=AsyncMock(side_effect=[
        '```html\n<html><head></head><body><h1 data-hero-headline>Home</h1></body></html>\n```\n```css\nh1{color:#c33}\n```',
        '```javascript\nfunction broken() {',
        '```javascript\nconsole.log("ready");\n```',
    ]))
    compiler = Mock(validate_javascript=AsyncMock())
    with patch("app.core.static_html_generator.get_llm_client", return_value=llm), \
         patch("app.core.static_html_generator.get_compiler_client", return_value=compiler), \
         patch("app.core.static_html_generator._upload_to_s3", return_value=None) as upload:
        result = asyncio.run(generate_static_html(master_brief=brief(), extraction=red_extraction(), variant_type="html_v2", site_id="site"))
    compiler.validate_javascript.assert_awaited_once_with('console.log("ready");')
    assert upload.call_count == 2
    assert "clip-path: none" in result["html"]
    assert "console.log" in result["html"]


def test_invalid_javascript_cannot_publish_any_assets():
    llm = Mock(generate_text=AsyncMock(side_effect=[
        '```html\n<html><head></head><body><h1>Home</h1></body></html>\n```\n```css\nh1{color:red}\n```',
        '```javascript\nfunction broken() {\n```',
        '```javascript\nfunction broken() {\n```',
    ]))
    compiler = Mock(validate_javascript=AsyncMock(side_effect=ValueError("Unexpected end of input")))
    with patch("app.core.static_html_generator.get_llm_client", return_value=llm), \
         patch("app.core.static_html_generator.get_compiler_client", return_value=compiler), \
         patch("app.core.static_html_generator._upload_to_s3") as upload:
        with pytest.raises(ValueError, match="Unexpected end"):
            asyncio.run(generate_static_html(master_brief=brief(), extraction=extraction(), variant_type="html_v2", site_id="site"))
    upload.assert_not_called()
