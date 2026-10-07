"""Generate client-facing names and descriptions for generated sites."""

from __future__ import annotations

import logging
from typing import Any

from app.core.llm import get_llm_client

logger = logging.getLogger(__name__)


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _fallback_identity(
    *, company_name: str, strategy: dict[str, Any], brief: Any
) -> tuple[str, str]:
    mode = str(strategy.get("designMode") or "designed").lower()
    direction_names = {
        "corporate": "Signature",
        "editorial": "Editorial",
        "immersive": "Immersive",
        "interactive": "Momentum",
        "minimalist": "Essential",
        "playful": "Brightside",
    }
    direction = direction_names.get(mode, "Studio")
    name = f"{company_name} {direction}".strip()
    concept = _value(_value(brief, "creativeDirection", {}), "designConcept", "")
    visual_style = _value(brief, "visualStyle", "")
    value_prop = _value(brief, "valueProposition", "")
    detail = concept or visual_style or mode
    benefit = value_prop or f"{company_name}'s services"
    description = (
        f"A {direction.lower()} design for {company_name}, pairing {detail} "
        f"with a clear focus on {benefit}."
    )
    return name[:80], description[:280]


async def generate_site_identity(
    *,
    company_name: str | None,
    industry: str | None,
    strategy: dict[str, Any],
    brief: Any,
    site: Any,
    existing_names: list[str] | None = None,
) -> tuple[str, str]:
    """Return a concise, lead-specific design name and description."""
    brand_name = (company_name or "This brand").strip()
    creative = _value(brief, "creativeDirection", {})
    hero = _value(site, "heroVariant", {})
    palette = _value(site, "paletteMode", "")
    existing = [name for name in (existing_names or []) if name]

    prompt = f"""Create client-facing naming for one newly generated website design.
Return only a JSON object with string fields `name` and `description`.

Brand / lead: {brand_name}
Industry: {industry or "not specified"}
Design type: {strategy.get("variantType", "website")}
Design mode: {strategy.get("designMode", "")}
Design guidance: {strategy.get("creativeBriefGuidance", "")}
Inspiration: {", ".join(strategy.get("inspirationKeywords", []))}
Actual theme: {_value(site, "themeName", "")}
Actual theme rationale: {_value(site, "themeRationale", "")}
Palette: {palette}
Creative concept: {_value(creative, "designConcept", "")}
Hero treatment: {_value(creative, "heroTreatment", "")}
Color mood: {_value(creative, "colorMood", "")}
Typography: {_value(creative, "typographyPersonality", "")}
Hero headline: {_value(hero, "headline", "")}
Hero supporting text: {_value(hero, "subheadline", "")}
Business value: {_value(brief, "valueProposition", "")}
Audience: {_value(brief, "primaryAudience", "")}
Names already used for this lead: {", ".join(existing) or "none"}

Requirements:
- Give this specific design a memorable name of 2 to 5 words, grounded in the brand and its visual concept. Avoid generic labels such as "Bold Startup", "Creative Alternative", or "Professional Standard".
- Make the name distinct from the other names already used for this lead. Do not just append a number.
- Write one polished description sentence (12 to 25 words) that connects the visual choices to this brand and its customers. Avoid unsupported claims and generic filler.
- Do not include quotation marks or markdown in either value."""

    fallback_name, fallback_description = _fallback_identity(
        company_name=brand_name, strategy=strategy, brief=brief
    )
    try:
        llm = get_llm_client()
        response = await llm.generate_text(
            prompt=prompt, temperature=0.75, max_tokens=500
        )
        data = llm.extract_json_from_response(response)
        name = str(data.get("name", "")).strip().strip('"\'')
        description = str(data.get("description", "")).strip().strip('"\'')
        if not name or not description:
            raise ValueError("AI response omitted the site name or description")
        generic_names = {
            "bold startup",
            "creative alternative",
            "professional standard",
            "minimal luxe",
            "next.js site",
        }
        existing_normalized = {item.casefold() for item in existing}
        if name.casefold() in generic_names or name.casefold() in existing_normalized:
            return fallback_name, fallback_description
        return name[:80], description[:280]
    except Exception:
        logger.exception(
            "AI site naming failed for brand %s; using a contextual fallback",
            brand_name,
        )
        return fallback_name, fallback_description
