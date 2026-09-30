from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from app.core.generated_runtime_validation import (
    validate_generated_html,
    validate_generated_javascript,
)
from app.core.compiler_capabilities import capability_manifest_for_source, hero_archetype_errors
from app.core.generated_content_contracts import generated_content_contract_errors
from app.core.screenshot_comparator import (
    rendered_structural_difference,
    rendered_variant_difference_score,
    rendered_visual_difference,
)
from app.core.semantic_validation import validate_semantics
from app.core.static_html_generator import (
    _build_static_html_prompt,
    _inject_static_seo_contract,
    _validate_static_discoverability_contract,
    _validate_static_form_contract,
)
from app.core.visual_adapter import build_art_direction_plan, build_visual_adapter


def _png(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (40, 40), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_static_runtime_reuses_tsx_security_boundary() -> None:
    unsafe = "fetch('/x'); localStorage.setItem('x', 'y'); navigator.sendBeacon('/x');"
    assert validate_generated_javascript(unsafe)
    assert validate_generated_javascript(
        "document.addEventListener('DOMContentLoaded', () => requestAnimationFrame(() => {}));"
    ) == []


def test_static_html_rejects_inline_scripts_and_event_handlers() -> None:
    assert validate_generated_html('<button onclick="fetch(\'/x\')">Go</button>')
    assert validate_generated_html("<script>navigator.sendBeacon('/x')</script>")
    assert validate_generated_html(
        '<script type="application/ld+json">{"@type":"WebPage"}</script>'
    ) == []


def test_visual_adapter_plan_contains_generated_conceptual_asset() -> None:
    extraction = SimpleNamespace(summary=SimpleNamespace(companyName="Works", serviceClues=[]))
    brief = SimpleNamespace(visualStyle="editorial", valueProposition="Make operations clearer")
    adapter = build_visual_adapter(extraction, brief, industry="architecture")
    plan = build_art_direction_plan(adapter, {"variantType": "html_v3"})
    asset = plan["conceptualImageRequirements"]["generatedVisualAsset"]
    assert asset["assetType"] == "inline-svg"
    assert asset["assetUrl"].startswith("data:image/svg+xml,")


def test_conceptual_visual_uses_industry_specific_visual_grammar() -> None:
    extraction = SimpleNamespace(summary=SimpleNamespace(companyName="Studio", serviceClues=["projects"]))
    brief = SimpleNamespace(visualStyle="editorial", valueProposition="Make space useful")
    architecture = build_art_direction_plan(
        build_visual_adapter(extraction, brief, industry="architecture"),
        {"variantType": "html_v1"},
    )["conceptualImageRequirements"]["generatedVisualAsset"]
    manufacturing = build_art_direction_plan(
        build_visual_adapter(extraction, brief, industry="manufacturing"),
        {"variantType": "html_v1"},
    )["conceptualImageRequirements"]["generatedVisualAsset"]
    assert architecture["visualGrammar"] != manufacturing["visualGrammar"]
    assert architecture["assetUrl"] != manufacturing["assetUrl"]


def test_static_prompt_is_explicitly_native_only_and_contains_adapter_plan() -> None:
    brief = SimpleNamespace(
        businessGoal="Book consultations", primaryAudience="Clients", valueProposition="Clear design",
        toneAndVoice="Calm", visualStyle="Editorial", colorStrategy="Warm", motionLevel="subtle",
        creativeDirection=SimpleNamespace(
            designConcept="Editorial", heroTreatment="Image-led", signatureTechnique="Reveal",
            layoutStrategy="Asymmetric", scrollBehavior="Measured", colorMood="Warm",
            typographyPersonality="Refined", microInteractions=[], inspirationKeywords=[], avoidPatterns=[]
        ), headline="Make space useful", subheadline="A clear next step.", sections=[],
        ctaStrategy="Book a call", brandAssets=SimpleNamespace(
            logoUrl=None, logoLightUrl=None, logoDarkUrl=None, logoVariants=[], primaryColor=None,
            secondaryColor=None, fontFamily=None, fontUrl=None, imageInventory=[], imageUrls=[]
        ), contactInfo={},
    )
    extraction = SimpleNamespace(summary=SimpleNamespace(companyName="Studio"), contactInfo=SimpleNamespace(model_dump=lambda **_: {}), analysis=SimpleNamespace(industry="architecture"))
    prompt = _build_static_html_prompt(brief, extraction, "html_v3")
    assert "no GSAP, Lenis, Embla, Three.js, React" in prompt
    assert "EVIDENCE-LED ART DIRECTION PLAN" in prompt
    assert "generatedVisualAsset" in prompt


def test_image_led_hero_requires_meaningful_approved_media_role() -> None:
    approved = "https://assets.example.test/hero.jpg"
    html = f'''<!doctype html><html><head></head><body><header class="hero"><img src="{approved}" alt="Project exterior" data-hero-media width="1200" height="800" loading="eager" sizes="100vw"></header></body></html>'''
    result = validate_semantics(
        html,
        require_media=True,
        approved_images={approved},
        require_hero_media=True,
    )
    assert result.valid


def test_static_seo_and_form_contracts_are_enforced() -> None:
    html = """<!doctype html><html><head><title>Studio</title><meta name="description" content="A studio"><meta name="viewport" content="width=device-width"><meta property="og:title" content="Studio"><meta property="og:description" content="A studio"><meta property="og:type" content="website"><meta property="og:url" content="https://example.test/studio"><link rel="canonical" href="https://example.test/studio"><link rel="icon" href="data:image/svg+xml,%3Csvg%3E%3C/svg%3E"><script type="application/ld+json">{"@type":"Organization","name":"Studio"}</script></head><body><form method="post" action="__LENMANAG_FORM_ENDPOINT__"><input name="name"><input name="email" type="email"><textarea name="message"></textarea><input name="website" tabindex="-1"></form></body></html>"""
    _validate_static_discoverability_contract(html)
    _validate_static_form_contract(html)
    with pytest.raises(ValueError, match="native POST"):
        _validate_static_form_contract(html.replace('method="post"', 'method="get"'))


def test_static_seo_identity_is_deterministic() -> None:
    source = """<!doctype html><html><head><title>Studio</title><meta name="description" content="A studio"><meta name="viewport" content="width=device-width"><meta property="og:title" content="Studio"><meta property="og:description" content="A studio"><meta property="og:type" content="website"><meta property="og:url" content="https://wrong.test"><link rel="canonical" href="https://wrong.test"><link rel="icon" href="data:image/svg+xml,%3Csvg%3E%3C/svg%3E"><script type="application/ld+json">{"@type":"Organization"}</script></head><body></body></html>"""
    extraction = SimpleNamespace(
        summary=SimpleNamespace(companyName="Studio", positioningSummary="A studio")
    )
    expected = "https://sites.example/st/real-slug"
    generated = _inject_static_seo_contract(source, extraction, expected)
    _validate_static_discoverability_contract(generated, expected_canonical_url=expected)
    assert expected in generated


def test_rendered_variant_difference_is_not_hash_only() -> None:
    assert rendered_visual_difference(_png((0, 0, 0)), _png((255, 255, 255))) > 0.9
    assert rendered_visual_difference(_png((0, 0, 0)), _png((0, 0, 0))) == 0


def test_rendered_variant_gate_requires_structural_evidence() -> None:
    first = Image.new("RGB", (96, 96), (20, 20, 20))
    second = Image.new("RGB", (96, 96), (220, 220, 220))
    first_bytes = BytesIO()
    second_bytes = BytesIO()
    first.save(first_bytes, format="PNG")
    second.save(second_bytes, format="PNG")
    evidence = rendered_variant_difference_score(first_bytes.getvalue(), second_bytes.getvalue())
    assert evidence["paletteOnly"] is True
    assert evidence["distinct"] is False
    assert rendered_structural_difference(first_bytes.getvalue(), second_bytes.getvalue()) < 0.05


def test_webgl_fallback_requires_real_markup_not_a_comment() -> None:
    comment_only = "import * as THREE from 'three'; // fallback: use SVG"
    real_fallback = "import * as THREE from 'three'; return supportsWebGL ? <canvas/> : <svg data-webgl-fallback='true'/>"
    assert capability_manifest_for_source(comment_only, runtime_mode="compiled-react-entry")["webglFallback"] is False
    assert capability_manifest_for_source(real_fallback, runtime_mode="compiled-react-entry")["webglFallback"] is True


def _hero_brief(archetype: str, image: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        heroArchetype=archetype,
        brandAssets=SimpleNamespace(
            imageUrls=[image] if image else [],
            imageInventory=[],
        ),
    )


def test_hero_archetype_contract_covers_creative_modes() -> None:
    assert not hero_archetype_errors(
        "<header class='hero'><h1>Make work clearer</h1></header>",
        _hero_brief("typography"),
    )
    assert not hero_archetype_errors(
        "<header class='hero'><h1>Make work clearer</h1><svg data-hero-visual='true'></svg></header>",
        _hero_brief("svg_diagram"),
    )
    assert not hero_archetype_errors(
        "<header class='hero'><h1>Make work clearer</h1></header>",
        _hero_brief("motion_graphic"),
        css="@keyframes rise { from { opacity: 0; } to { opacity: 1; } } .hero { animation: rise 1s ease; }",
    )
    assert hero_archetype_errors(
        "<header class='hero'><h1>Make work clearer</h1></header>",
        _hero_brief("motion_graphic"),
    )


def test_webgl_hero_archetype_requires_approved_capability_and_fallback() -> None:
    brief = _hero_brief("webgl_fallback")
    missing_fallback = "import * as THREE from 'three'; const scene = new THREE.Scene(); return <header class='hero'><h1>Work</h1>{supportsWebGL ? <canvas/> : null}</header>;"
    assert hero_archetype_errors(missing_fallback, brief)
    with_fallback = "import * as THREE from 'three'; const scene = new THREE.Scene(); return <header class='hero'><h1>Work</h1>{supportsWebGL ? <canvas/> : <svg data-webgl-fallback='true'/>}</header>;"
    assert not hero_archetype_errors(with_fallback, brief)


def test_photography_hero_archetype_requires_approved_image_in_hero() -> None:
    image = "https://assets.example.test/hero.jpg"
    brief = _hero_brief("photography", image)
    assert not hero_archetype_errors(
        f"<header class='hero'><img src='{image}' alt='Project' /></header>",
        brief,
    )
    assert hero_archetype_errors(
        "<header class='hero'><img src='https://other.example.test/hero.jpg' /></header>",
        brief,
    )


def test_content_contract_ignores_comments_and_handles_split_visible_copy() -> None:
    brief = SimpleNamespace(
        headline="Make work clearer",
        subheadline="A better operating rhythm.",
        conversionAction="Book a call",
        sections=[],
        extractedContent={},
        contactInfo={},
        brandAssets=SimpleNamespace(primaryColor="#123456", secondaryColor="#abcdef"),
    )
    extraction = SimpleNamespace(analysis=None, summary=SimpleNamespace(serviceClues=[]), contactInfo=None)
    html = """<!doctype html><html><body><!-- Make work clearer --><section><h1>Make <em>work</em> clearer</h1><p>A better operating rhythm.</p><a href='#contact'>Book a call</a></section><section><p>Contact</p></section><section><p>Footer</p></section></body></html>"""
    errors = generated_content_contract_errors(html, brief, extraction, rendered_html=True, css=":root { --primary: #123456; --secondary: rgb(171,205,239); }")
    assert not any("headline" in error for error in errors)
