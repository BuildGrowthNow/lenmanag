"""Evidence-led visual adaptation and art-direction planning.

This module deliberately uses small, explainable rules.  The adapter is not a
second source of business facts: it describes design consequences of evidence
already present in extraction and the approved brief.
"""

from __future__ import annotations

from typing import Any


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
    detected = next((name for name, words in signals.items() if any(word in evidence or word in label for word in words)), "general")
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
    plan = {"creativeConcept": f"{lenses.get(variant, 'a faithful interpretation')} of {adapter.get('industry')} through {adapter.get('metaphors', ['clarity'])[0]} and source-backed evidence.", "heroComposition": strategy.get("heroComposition") or "editorial headline paired with the strongest approved evidence", "layoutSystem": strategy.get("layoutSystem") or adapter.get("metaphors", ["structured composition"]), "sectionRhythm": strategy.get("sectionRhythm") or adapter.get("interaction", ["progressive disclosure"]), "approvedImageUsage": adapter.get("imagery", []), "conceptualImageRequirements": {"needed": bool(adapter.get("conceptual")), "brief": f"Subject: {', '.join(adapter.get('imagery', []))}; relationship: {adapter.get('industry')}; exclude unsupported claims, logos, people, locations, or metrics."}, "svgOrDiagramOpportunities": adapter.get("interaction", []), "interactionConcept": adapter.get("interaction", ["progressive disclosure"])[0], "animationConcept": adapter.get("motion"), "mobileBehavior": "collapse to one readable flow; preserve image crops, focus order, touch targets, and visible content", "typographySystem": adapter.get("type"), "colorBehavior": adapter.get("color"), "accessibilityRequirements": ["semantic landmarks", "visible focus", "reduced-motion support", "meaningful alt text", "keyboard-complete interaction"], "performanceRisks": ["large images", "scroll choreography", "unnecessary canvas or WebGL"], "fallbackPlan": "retain the semantic content and CSS composition if JavaScript, imagery, or advanced rendering is unavailable", "capabilities": select_capabilities(adapter, variant), "industry": adapter.get("industry"), "audience": adapter.get("audience")}
    return plan


build_industry_visual_adapter = build_visual_adapter
