"""Evidence-led visual adaptation and art-direction planning.

This module deliberately uses small, explainable rules.  The adapter is not a
second source of business facts: it describes design consequences of evidence
already present in extraction and the approved brief.
"""

from __future__ import annotations

import hashlib
from html import escape
from typing import Any
from urllib.parse import quote


def _value(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default) if obj is not None else default


def _text(extraction: Any, brief: Any) -> str:
    parts: list[str] = []
    summary = _value(extraction, "summary")
    analysis = _value(extraction, "analysis")
    for obj, fields in (
        (summary, ("companyName", "positioningSummary", "audienceClues", "serviceClues", "toneClues")),
        (analysis, ("positioning", "audience", "services", "tone", "valueProposition")),
        (brief, ("businessGoal", "primaryAudience", "valueProposition", "toneAndVoice", "visualStyle")),
    ):
        for field in fields:
            value = _value(obj, field, "")
            if isinstance(value, (list, tuple)):
                parts.extend(str(item) for item in value)
            elif value:
                parts.append(str(value))
    for image in _value(extraction, "extractedImages", []) or []:
        parts.extend(str(_value(image, key, "")) for key in ("altText", "title", "category"))
    for section in (_value(extraction, "sectionInventory", []) or [])[:20]:
        parts.extend(str(_value(section, key, "")) for key in ("heading", "text", "type"))
    return " ".join(parts).lower()


def build_visual_adapter(extraction: Any, brief: Any = None, industry: str | None = None) -> dict[str, Any]:
    """Return structured visual guidance grounded in extracted evidence."""
    evidence = _text(extraction, brief)
    label = (industry or "").lower()
    signals = {
        "restaurant": ("restaurant", "food", "menu", "dining", "cafe", "catering"),
        "clinic": ("clinic", "medical", "health", "dental", "therapy", "patient"),
        "architecture": ("architect", "architecture", "interior", "studio", "project portfolio"),
        "legal": ("legal", "law firm", "attorney", "litigation", "practice area"),
        "manufacturing": ("manufactur", "machinery", "fabricat", "industrial", "plant", "production"),
        "creative": ("creative studio", "branding", "design studio", "photography", "agency", "artist"),
        "home_services": ("plumb", "hvac", "roof", "remodel", "landscap", "home service", "contractor", "well drilling"),
        "finance": ("financial", "finance", "wealth", "accounting", "investment", "insurance"),
    }
    explicit = next(
        (name for name, words in signals.items() if any(word in label for word in words)),
        None,
    )
    detected = explicit or next(
        (name for name, words in signals.items() if any(word in evidence for word in words)),
        "general",
    )
    profiles: dict[str, dict[str, Any]] = {
        "restaurant": {"subcategory": "hospitality and dining", "audience": "guests choosing where and how to dine", "trust": ["menu clarity", "real food and space imagery", "reservation confidence"], "imagery": ["food", "room atmosphere", "ingredients"], "metaphors": ["rhythm", "course", "table", "seasonality"], "interaction": ["menu rhythm", "reservation flow", "ingredient storytelling"], "motion": "sensory, paced transitions", "type": "expressive display with highly legible body text", "color": "appetite-led accents with disciplined contrast", "avoid": ["generic SaaS cards", "unrelated stock food", "overly playful UI"], "conceptual": True, "capabilities": ["svg", "native-scroll", "carousel"]},
        "clinic": {"subcategory": "health and care", "audience": "people seeking a clear, reassuring care decision", "trust": ["treatment pathways", "staff and facility evidence", "accessibility"], "imagery": ["staff", "facility", "care context"], "metaphors": ["pathway", "care journey", "calm progression"], "interaction": ["treatment pathway", "accessible accordions", "appointment flow"], "motion": "calm, low-amplitude transitions", "type": "warm, highly legible humanist sans", "color": "calm base with restrained reassuring accents", "avoid": ["fear-based urgency", "medical claims", "busy motion"], "conceptual": False, "capabilities": ["native-scroll", "svg"]},
        "architecture": {"subcategory": "built environment and spatial design", "audience": "clients evaluating expertise through work and process", "trust": ["project documentation", "materials", "measured process"], "imagery": ["projects", "materials", "spatial details"], "metaphors": ["space", "threshold", "grid", "section"], "interaction": ["project sequencing", "measured scroll", "material detail reveal"], "motion": "measured, spatial transitions", "type": "architectural display face paired with precise sans", "color": "material-led neutrals with one intentional accent", "avoid": ["generic bento grids", "neon effects", "unverified project claims"], "conceptual": True, "capabilities": ["svg", "native-scroll", "carousel"]},
        "legal": {"subcategory": "legal professional services", "audience": "people or organizations making a high-trust legal decision", "trust": ["practice-area clarity", "authority", "plain-language guidance"], "imagery": ["office", "people", "document details"], "metaphors": ["clarity", "path", "precedent", "structure"], "interaction": ["practice-area navigation", "guided inquiry", "progressive disclosure"], "motion": "restrained, confident transitions", "type": "authoritative serif or refined sans with excellent readability", "color": "quiet authority with restrained contrast", "avoid": ["legal guarantees", "dramatic gimmicks", "invented outcomes"], "conceptual": False, "capabilities": ["native-scroll", "svg"]},
        "manufacturing": {"subcategory": "industrial manufacturing", "audience": "buyers and partners assessing capability and fit", "trust": ["process", "materials", "machinery", "technical evidence"], "imagery": ["machinery", "materials", "finished work"], "metaphors": ["flow", "assembly", "tolerance", "transformation"], "interaction": ["process diagram", "material journey", "capability sequence"], "motion": "precise, functional movement", "type": "technical sans with strong numeric and label hierarchy", "color": "industrial base with high-visibility functional accents", "avoid": ["dashboard cosplay", "unsupported metrics", "decorative 3D"], "conceptual": True, "capabilities": ["svg", "native-scroll", "diagram"]},
        "creative": {"subcategory": "creative practice", "audience": "clients selecting taste, point of view, and execution quality", "trust": ["portfolio quality", "process", "distinctive point of view"], "imagery": ["portfolio work", "studio details", "making process"], "metaphors": ["material", "edit", "composition", "sequence"], "interaction": ["image sequencing", "expressive SVG", "portfolio focus"], "motion": "expressive but choreographed", "type": "art-directed display typography with disciplined supporting text", "color": "brand-led and compositionally intentional", "avoid": ["decorative blobs", "generic agency tropes", "random stock"], "conceptual": True, "capabilities": ["svg", "native-scroll", "carousel"]},
        "home_services": {"subcategory": "home and field services", "audience": "property owners seeking reassurance and a practical next step", "trust": ["real work", "craftsmanship", "finished results", "clear contact flow"], "imagery": ["real work", "craft details", "finished results"], "metaphors": ["before and after", "craft", "repair", "care"], "interaction": ["service journey", "before-after sequence", "practical contact flow"], "motion": "grounded, helpful transitions", "type": "confident humanist sans with clear hierarchy", "color": "grounded brand colors with strong action contrast", "avoid": ["fake urgency", "invented guarantees", "generic service icon grids"], "conceptual": False, "capabilities": ["native-scroll", "svg"]},
        "finance": {"subcategory": "financial services", "audience": "people or businesses seeking confidence and clarity in a financial decision", "trust": ["clarity", "evidence", "data-informed explanation"], "imagery": ["people", "work context", "approved data visuals"], "metaphors": ["signal", "path", "confidence", "progress"], "interaction": ["guided comparison", "explained data", "progressive disclosure"], "motion": "restrained and purposeful", "type": "clear contemporary sans with a considered display contrast", "color": "confidence-first contrast with restrained accents", "avoid": ["guaranteed returns", "trading dashboard cosplay", "invented metrics"], "conceptual": False, "capabilities": ["svg", "native-scroll", "chart-if-approved-data"]},
    }
    profile = profiles.get(detected, {"subcategory": "evidence-led business", "audience": "the audience described in the approved brief", "trust": ["clear positioning", "source-backed proof", "easy next step"], "imagery": ["approved client imagery"], "metaphors": ["journey", "craft", "clarity"], "interaction": ["progressive disclosure"], "motion": "subtle and purposeful", "type": "refined, legible web typography", "color": "brand-led with accessible contrast", "avoid": ["generic templates", "random stock", "unsupported claims"], "conceptual": False, "capabilities": ["native-scroll", "svg"]})
    return {"industry": detected, "subcategory": profile["subcategory"], "audience": _value(_value(extraction, "analysis"), "audience") or _value(brief, "primaryAudience") or profile["audience"], "evidenceSignals": [word for word in signals.get(detected, ()) if word in evidence][:12], **profile}


def select_capabilities(adapter: dict[str, Any], variant_type: str) -> dict[str, Any]:
    """Select only capabilities justified by the adapter and variant lens."""
    base = list(adapter.get("capabilities", []))
    if variant_type == "html_v2":
        base.append("layered-scroll")
    if variant_type == "html_v3" and "svg" not in base:
        base.append("svg")
    return {"allowed": list(dict.fromkeys(base)), "fallbacks": {cap: "semantic HTML and CSS" for cap in base}, "forbiddenUnlessJustified": ["webgl", "canvas", "third-party runtime libraries"]}


def build_art_direction_plan(adapter: dict[str, Any], strategy: dict[str, Any], brief: Any = None, extraction: Any = None) -> dict[str, Any]:
    """Create the implementation contract consumed by a code generator."""
    variant = strategy.get("variantType", "html_v1")
    lenses = {"html_v1": "the most credible and refined interpretation", "html_v2": "the most memorable commercially appropriate interpretation", "html_v3": "a clearly contrasting but faithful creative interpretation"}
    conceptual = _build_conceptual_svg_asset(adapter, variant)
    plan = {"creativeConcept": f"{lenses.get(variant, 'a faithful interpretation')} of {adapter.get('industry')} through {adapter.get('metaphors', ['clarity'])[0]} and source-backed evidence.", "heroComposition": strategy.get("heroComposition") or "editorial headline paired with the strongest approved evidence", "layoutSystem": strategy.get("layoutSystem") or adapter.get("metaphors", ["structured composition"]), "sectionRhythm": strategy.get("sectionRhythm") or adapter.get("interaction", ["progressive disclosure"]), "approvedImageUsage": adapter.get("imagery", []), "conceptualImageRequirements": {"needed": bool(adapter.get("conceptual")), "brief": f"Subject: {', '.join(adapter.get('imagery', []))}; relationship: {adapter.get('industry')}; exclude unsupported claims, logos, people, locations, or metrics.", "generatedVisualAsset": conceptual}, "svgOrDiagramOpportunities": adapter.get("interaction", []), "interactionConcept": adapter.get("interaction", ["progressive disclosure"])[0], "animationConcept": adapter.get("motion"), "mobileBehavior": "collapse to one readable flow; preserve image crops, focus order, touch targets, and visible content", "typographySystem": adapter.get("type"), "colorBehavior": adapter.get("color"), "accessibilityRequirements": ["semantic landmarks", "visible focus", "reduced-motion support", "meaningful alt text", "keyboard-complete interaction"], "performanceRisks": ["large images", "scroll choreography", "unnecessary canvas or WebGL"], "fallbackPlan": "retain the semantic content and CSS composition if JavaScript, imagery, or advanced rendering is unavailable", "capabilities": select_capabilities(adapter, variant), "industry": adapter.get("industry"), "audience": adapter.get("audience")}
    return plan


def _build_conceptual_svg_asset(adapter: dict[str, Any], variant: str) -> dict[str, str] | None:
    """Create a deterministic, evidence-shaped inline illustrative asset.

    Each industry gets a different visual grammar, not just a palette swap.
    A small evidence-derived seed keeps repeated generations stable while
    changing the composition when the extracted signals or variant lens change.
    """
    if not adapter.get("conceptual"):
        return None
    palettes = {
        "html_v1": ("#0f172a", "#c08457", "#fef3c7"),
        "html_v2": ("#111827", "#22d3ee", "#a78bfa"),
        "html_v3": ("#173b3f", "#f59e0b", "#f5d0a9"),
    }
    background, accent, highlight = palettes.get(variant, palettes["html_v1"])
    industry_value = str(adapter.get("industry", "business"))
    industry = escape(industry_value)
    metaphors = [str(value) for value in adapter.get("metaphors", []) if value]
    metaphor_value = metaphors[0] if metaphors else "craft"
    metaphor = escape(metaphor_value)
    signals = [str(value) for value in adapter.get("evidenceSignals", []) if value]
    seed = int(
        hashlib.sha256(
            f"{industry_value}|{metaphor_value}|{'|'.join(signals)}|{variant}".encode()
        ).hexdigest()[:8],
        16,
    )
    shift = seed % 54
    motif = ""
    if industry_value == "architecture":
        motif = (
            f'<g fill="none" stroke="{highlight}" stroke-width="6" opacity=".8">'
            f'<path d="M80 {470-shift%35}L250 {150+shift%40}L470 {390-shift%55}L730 {100+shift%50}"/>'
            f'<path d="M150 530L320 205L560 470L690 190"/><path d="M110 150H690M150 210H620M190 270H570"/></g>'
            f'<path d="M110 510L250 150L470 390L730 100V600H110Z" fill="{accent}" opacity=".5"/>'
        )
    elif industry_value == "manufacturing":
        motif = (
            f'<g fill="none" stroke="{highlight}" stroke-width="10" opacity=".9">'
            f'<circle cx="{170+shift}" cy="190" r="62"/><circle cx="{420-shift%80}" cy="390" r="92"/>'
            f'<path d="M70 500H730M100 455H690"/><path d="M170 252V430M420 298V480"/></g>'
            f'<path d="M70 500H730V570H70Z" fill="{accent}" opacity=".72"/>'
        )
    elif industry_value == "restaurant":
        motif = (
            f'<g fill="{highlight}" opacity=".88"><circle cx="220" cy="300" r="116"/>'
            f'<circle cx="590" cy="240" r="82"/><circle cx="520" cy="470" r="72"/></g>'
            f'<g fill="none" stroke="{accent}" stroke-width="18" stroke-linecap="round">'
            f'<path d="M90 120C250 {80+shift%50} 360 {220+shift%40} 720 110"/>'
            f'<path d="M90 520C260 360 430 590 720 390"/></g>'
        )
    elif industry_value == "creative":
        motif = (
            f'<g opacity=".88"><rect x="90" y="110" width="270" height="330" rx="18" fill="{accent}" transform="rotate({-8+shift%16} 225 275)"/>'
            f'<rect x="390" y="170" width="270" height="300" rx="18" fill="{highlight}" transform="rotate({6-shift%12} 525 320)"/>'
            f'<path d="M110 500L270 340L390 470L700 120" fill="none" stroke="{background}" stroke-width="22"/></g>'
        )
    else:
        motif = (
            f'<path d="M0 {430-shift%70} C140 {270+shift%60} 260 {520-shift%80} '
            f'410 {340+shift%50} S650 {120+shift%80} 800 {250+shift%60} V600 H0Z" fill="{accent}" opacity=".72"/>'
            f'<circle cx="{520+shift%100}" cy="{150+shift%120}" r="{80+shift%38}" fill="{highlight}" opacity=".9"/>'
            f'<path d="M90 470L{260+shift%90} 300L{420-shift%70} 410L690 160" fill="none" stroke="{highlight}" stroke-width="12" stroke-linecap="round"/>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" role="img" '
        f'data-industry="{industry}" data-motif="{escape(metaphor_value)}" '
        f'aria-labelledby="title desc"><title id="title">Conceptual {industry} visual</title>'
        f'<desc id="desc">An evidence-led {industry} composition expressing {metaphor}.</desc>'
        f'<rect width="800" height="600" fill="{background}"/>{motif}'
        f'<text x="72" y="80" fill="{highlight}" font-family="system-ui,sans-serif" font-size="22" letter-spacing="4">{escape(industry_value.upper())}</text>'
        '</svg>'
    )
    return {
        "assetType": "inline-svg",
        "assetUrl": "data:image/svg+xml," + quote(svg, safe=""),
        "altText": f"Evidence-led {industry_value} visual expressing {metaphor_value}",
        "visualGrammar": industry_value,
        "evidenceSignals": ", ".join(signals[:4]),
    }


build_industry_visual_adapter = build_visual_adapter
