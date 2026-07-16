from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, cast
from uuid import uuid4

from app.core.analytics import analytics_repository
from app.core.color_system import generate_color_system
from app.core.config import get_settings
from app.core.industry_detection import detect_industry, get_industry_design_config
from app.core.leads import lead_repository
from app.core.llm import get_llm_client
from app.core.mongo import get_database
from app.core.screenshot_comparator import ScreenshotComparator
from app.schemas.brief import SiteBrief, VisualCritique, VisualRedesignBrief
from app.schemas.extraction import ExtractionSnapshot
from app.schemas.lead import JobSummary
from app.schemas.site import (
    BrandTokens,
    CtaStrategy,
    GeneratedSite,
    GeneratedSiteVersion,
    GeneratedSiteVersionResponse,
    HeroVariant,
    PaletteMode,
    PublishApprovalState,
    RefinementPromptRecord,
    ReviewWorkflowState,
    SiteCompareResponse,
    SiteExportMetadata,
    SiteExportRecord,
    SiteGenerateRequest,
    SiteHandoffRecord,
    SiteOverrideCreateRequest,
    SiteOverrideRecord,
    SiteQaStatus,
    SiteReadinessStatus,
    SiteReviewChecklistItem,
    SiteReviewPatchRequest,
    SiteReviewQueueItem,
    SiteReviewQueueResponse,
    SiteReviewRecord,
    SiteReviewRequest,
    SiteScreenshotMetadata,
    SiteSection,
    SiteSourceAttribution,
    ThemeLibraryResponse,
    ThemeVariant,
)

logger = logging.getLogger(__name__)

THEME_LIBRARY: list[dict[str, Any]] = [
    {
        "id": "editorial-frame",
        "themeKey": "editorial-frame",
        "name": "Editorial Frame",
        "description": "Spacious, high-contrast composition with a strong editorial hierarchy and measured motion.",
        "heroFamily": "split-editorial",
        "sectionStack": ["hero", "proof", "services", "cta"],
        "motionPreset": "subtle",
        "typographyPairing": "serif-display + neutral-sans",
        "spacingStyle": "spacious",
        "colorTreatment": "monochrome with restrained accent",
        "bestForIndustries": ["consulting", "legal", "finance", "b2b services"],
        "placeholderPolicy": "No placeholders; unresolved data becomes an explicit operator gap.",
        "allowedPaletteModes": ["zinc", "light"],
    },
    {
        "id": "signal-panel",
        "themeKey": "signal-panel",
        "name": "Signal Panel",
        "description": "Balanced layout with distinct content blocks, a confident CTA bar, and a practical conversion rhythm.",
        "heroFamily": "stacked-panel",
        "sectionStack": ["hero", "audience", "proof", "cta"],
        "motionPreset": "moderate",
        "typographyPairing": "geometric-sans + neutral-sans",
        "spacingStyle": "balanced",
        "colorTreatment": "neutral surface with one high-contrast accent",
        "bestForIndustries": ["agency", "saas", "operations", "growth"],
        "placeholderPolicy": "Every missing requirement stays visible in the operator review surface.",
        "allowedPaletteModes": ["zinc", "light", "colorful"],
    },
    {
        "id": "color-study",
        "themeKey": "color-study",
        "name": "Color Study",
        "description": "Expressive palette-first design with layered cards and a more visual editorial presentation.",
        "heroFamily": "media-led",
        "sectionStack": ["hero", "brand", "services", "cta"],
        "motionPreset": "expressive",
        "typographyPairing": "humanist-sans + display-sans",
        "spacingStyle": "balanced",
        "colorTreatment": "vivid accent palette with visible brand color cues",
        "bestForIndustries": ["creative", "design", "education", "consumer"],
        "placeholderPolicy": "No filler content; use only approved source-grounded material or explicit gaps.",
        "allowedPaletteModes": ["colorful", "light"],
    },
    {
        "id": "minimal-luxe",
        "themeKey": "minimal-luxe",
        "name": "Minimal Luxe",
        "description": "Quiet, highly refined layout with subtle borders, restrained motion, and premium spacing.",
        "heroFamily": "centered-luxe",
        "sectionStack": ["hero", "proof", "cta"],
        "motionPreset": "subtle",
        "typographyPairing": "serif-display + elegant-sans",
        "spacingStyle": "spacious",
        "colorTreatment": "soft neutrals with a single accent channel",
        "bestForIndustries": [
            "real estate",
            "hospitality",
            "premium services",
            "advisory",
        ],
        "placeholderPolicy": "No placeholder metrics, testimonials, or demo imagery.",
        "allowedPaletteModes": ["zinc", "light"],
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_friendly_slug(company_name: str, existing_slugs: set[str]) -> str:
    """Generate a friendly URL slug from company name (max 8 chars).

    - Converts to lowercase
    - Removes special characters
    - Truncates to 8 characters
    - Adds numeric suffix if duplicate exists
    """
    import re

    # Remove special characters, convert to lowercase
    clean = re.sub(r"[^a-z0-9]", "", company_name.lower())

    # Truncate to 8 characters
    base_slug = clean[:8] if clean else "site"

    # If unique, return as-is
    if base_slug not in existing_slugs:
        return base_slug

    # Add numeric suffix if duplicate
    for i in range(2, 1000):
        # Truncate base to make room for suffix
        max_base_len = 8 - len(str(i))
        candidate = f"{base_slug[:max_base_len]}{i}"
        if candidate not in existing_slugs:
            return candidate

    # Fallback to UUID if somehow we can't find a unique slug
    import uuid

    return str(uuid.uuid4())[:8]


def _is_client_safe_cta(text: str) -> bool:
    settings = get_settings()
    if not text:
        return False
    lowered = text.lower()
    blocked = [
        p.strip().lower()
        for p in (settings.cta_blocked_phrases or "").split(",")
        if p.strip()
    ]
    for phrase in blocked:
        if phrase and phrase in lowered:
            return False
    allowed = [
        v.strip().lower()
        for v in (settings.cta_allowed_verbs or "").split(",")
        if v.strip()
    ]
    # require an allowed verb to appear as a whole word
    for verb in allowed:
        if re.search(rf"\b{re.escape(verb)}\b", lowered):
            return True
    return False


def _ensure_client_safe_cta(text: str) -> str:
    if _is_client_safe_cta(text):
        return text
    replacements = {
        "review the preview": "Explore the preview",
        "see source notes": "Learn more",
        "see the source trace": "Learn more",
        "see source traceability": "Learn more",
        "review the brief": "Get started",
    }
    lowered = (text or "").strip().lower()
    for k, v in replacements.items():
        if k in lowered:
            return v
    # fallback: pick a safe verb from allowed verbs
    allowed = [
        v.strip()
        for v in (get_settings().cta_allowed_verbs or "").split(",")
        if v.strip()
    ]
    return (allowed[0] + "") if allowed else "Learn more"


def _sanitize_public_copy(text: str) -> str:
    sanitized = text or ""
    # Replace internal terms with neutral/public equivalents or remove entirely
    replacements = {
        r"\boperator review surface\b": "review",
        r"\boperator review\b": "review",
        r"\boperators reviewing\b": "teams reviewing",
        r"\boperator\b": "team",
        r"\badmin\b": "workspace",
        r"\binternal\b": "project",
        r"\bsource[- ]safe\b": "",
        r"\bsource traceability\b": "",
        r"\bgeneration notes?\b": "",
        r"\bgenerated\b": "",
        r"\bgeneration\b": "",
        r"\bquality score\b": "",
        r"\bQA status\b": "",
        r"\breadiness\b": "",
        r"\bjob id\b": "",
        r"\bevidence\b": "",
        r"\binference labels?\b": "",
        r"\bextracted cues?\b": "",
        r"\bextracted logo\b": "logo",
        r"\bextracted color\b": "color",
        r"\bextracted typography\b": "typography",
        r"\bbrand cues?\b": "brand",
        r"\bconversion paths?\b": "next steps",
        r"\bCTA patterns?\b": "",
        r"\bCTA pattern\b": "",
        r"\bsource cues?\b": "",
        r"\bcrawl(ed|ing)?\b": "",
        r"\bextraction\b": "",
        r"\bbrief\b": "",
        r"\bmissing requirements?\b": "",
        r"\bpreview runtime\b": "",
        r"\bno logo asset captured\b": "",
        r"\bderived from (the )?selected palette\b": "",
    }
    for pattern, replacement in replacements.items():
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    # Remove leftover multiple spaces and artifacts like trailing punctuation
    sanitized = re.sub(r"\s{2,}", " ", sanitized).strip()
    sanitized = re.sub(r"\s+[.:;,-]$", "", sanitized)
    return sanitized


def _looks_operator_facing(text: str) -> bool:
    value = _text(text).lower()
    if not value:
        return False
    operator_terms = [
        "brand cues",
        "conversion path",
        "cta pattern",
        "open questions",
        "open question",
        "missing requirements",
        "gap item",
        "gap items",
        "extracted logo",
        "extracted color",
        "extracted typography",
        "extracted cues",
        "source cues",
        "source-safe",
        "source traceability",
        "operator review",
        "operator review surface",
        "preview runtime",
        "quality score",
        "qa status",
        "readiness",
        "job id",
    ]
    return any(term in value for term in operator_terms)


def validate_operator_prompt(prompt: str) -> tuple[bool, str]:
    """Validate operator refinement prompt for safety constraints."""
    blocked_terms = [
        "testimonial",
        "fake",
        "invented",
        "pricing",
        "price",
        "cost",
        "guarantee",
        "promise",
        "10x",
        "guaranteed",
        "exclusive offer",
    ]

    lower = (prompt or "").lower()
    for term in blocked_terms:
        if term in lower:
            return (
                False,
                f"Prompts cannot include '{term}'. Keep changes grounded in extracted source data.",
            )

    if len(prompt) < 10:
        return False, "Prompt must be at least 10 characters"

    if len(prompt) > 500:
        return False, "Prompt must be less than 500 characters"

    return True, ""


def _strip_instruction_leads(text: str) -> str:
    """Remove instructional preambles and labeled prefixes from a text blob."""
    value = _text(text)
    if not value:
        return ""
    # Remove common instruction preambles ending with a colon
    value = re.sub(
        r"^(use|leverage|make|choose|write)\b[^:]{0,120}:\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    # Remove labels like 'Homepage title:', 'Meta description:', 'Primary heading:', 'H1:'
    value = re.sub(
        r"\b(homepage\s+title|meta\s+description|primary\s+heading|h1)\s*:\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    # If the text still contains pipes or slashes as separators, keep the first meaningful fragment
    for sep in ["|", "—", "-", "\n"]:
        if sep in value:
            parts = [p.strip() for p in value.split(sep) if p.strip()]
            if parts:
                value = parts[0]
                break
    return _sanitize_public_copy(value)


def _compose_benefit_headline(extraction: ExtractionSnapshot) -> str | None:
    services = [s.strip() for s in (extraction.summary.serviceClues or []) if _text(s)]
    if not services:
        return None
    # Normalize to short action phrases
    clean = []
    for s in services[:3]:
        # remove trailing punctuation
        s2 = re.sub(r"[.;:,]+$", "", s)
        # ensure it starts with a verb-like phrase (heuristic)
        clean.append(s2)
    if not clean:
        return None
    if len(clean) == 1:
        phrase = clean[0]
    elif len(clean) == 2:
        phrase = f"{clean[0]} and {clean[1]}"
    else:
        phrase = f"{clean[0]}, {clean[1]}, and {clean[2]}"
    return _sanitize_public_copy(f"A better way to {phrase}")


def _compress_mission_line(text: str) -> str:
    """Lightly compress a mission sentence into a hero-ready fragment.

    Heuristic: if the text contains "is a" or "is an", drop the lead-in
    (often the brand name) and keep the descriptive tail. This helps move
    from "The Org is a charitable foundation..." toward a visitor-facing
    mission line like "Charitable foundation supporting..." without
    inventing new facts.
    """
    value = _sanitize_public_copy(_text(text))
    if not value:
        return value
    match = re.search(r"\bis an?\s+(.+)", value, flags=re.IGNORECASE)
    if match:
        remainder = match.group(1).strip(" .,:;-")
        if remainder:
            return remainder[0].upper() + remainder[1:]
    return value


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def _dedupe_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for ref in refs:
        key = "|".join(
            [
                str(ref.get("kind", "")),
                str(ref.get("sourceUrl", "")),
                str(ref.get("label", "")),
                str(ref.get("excerpt", "")),
                str(ref.get("confidence", "")),
                str(ref.get("evidenceType", "")),
                str(ref.get("assetType", "")),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    return unique


def _page_reference_from_citation(citation: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "page",
        "sourceUrl": citation["pageUrl"],
        "label": citation["label"],
        "excerpt": citation["excerpt"],
        "confidence": int(citation.get("confidence", 0)),
        "evidenceType": citation.get("evidenceType"),
        "assetType": None,
    }


def _asset_reference_from_cue(cue: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "asset",
        "sourceUrl": cue["sourceUrl"],
        "label": cue["label"],
        "excerpt": cue["value"],
        "confidence": int(cue.get("confidence", 0)),
        "evidenceType": None,
        "assetType": cue.get("assetType"),
    }


def _brief_evidence(
    *,
    source_kind: str,
    inference_label: str,
    confidence: int,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "sourceKind": source_kind,
        "inferenceLabel": inference_label,
        "confidence": int(confidence),
        "references": references or [],
    }


def _token(
    value: str,
    *,
    source_kind: str,
    inference_label: str,
    confidence: int,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "evidence": _brief_evidence(
            source_kind=source_kind,
            inference_label=inference_label,
            confidence=confidence,
            references=references,
        ),
    }


def _theme_data(theme_key: str) -> dict[str, Any]:
    for theme in THEME_LIBRARY:
        if theme["themeKey"] == theme_key:
            return theme
    return THEME_LIBRARY[0]


def _theme_for_signals(
    signals: str, extraction: ExtractionSnapshot
) -> tuple[dict[str, Any], str]:
    theme_scores = {theme["themeKey"]: 0 for theme in THEME_LIBRARY}
    if _contains_any(
        signals, ["premium", "executive", "authority", "consulting", "finance", "law"]
    ):
        theme_scores["editorial-frame"] += 4
    if _contains_any(
        signals, ["conversion", "lead", "book", "demo", "call", "performance", "growth"]
    ):
        theme_scores["signal-panel"] += 4
    if _contains_any(
        signals, ["creative", "brand", "visual", "studio", "color", "design"]
    ):
        theme_scores["color-study"] += 4
    if _contains_any(
        signals, ["minimal", "clean", "quiet", "refined", "luxe", "premium"]
    ):
        theme_scores["minimal-luxe"] += 4
    if extraction.brandAssetCues:
        color_cues = [
            cue for cue in extraction.brandAssetCues if cue.assetType == "color"
        ]
        if color_cues:
            if len(color_cues) >= 2 or any(
                _contains_any(
                    f"{cue.label} {cue.value}",
                    ["vibrant", "gradient", "multi", "colorful"],
                )
                for cue in color_cues
            ):
                theme_scores["color-study"] += 3
            else:
                theme_scores["signal-panel"] += 2
        if any(cue.assetType == "typography" for cue in extraction.brandAssetCues):
            theme_scores["editorial-frame"] += 2
        if any(cue.assetType == "logo" for cue in extraction.brandAssetCues):
            theme_scores["signal-panel"] += 1
    theme_key = max(theme_scores.items(), key=lambda item: (item[1], item[0]))[0]
    theme = _theme_data(theme_key)
    rationale = f"Selected {theme['name']} because the source cues lean toward {theme['colorTreatment'].lower()} and the extracted tone matches a {theme['spacingStyle']} layout."
    return theme, rationale


def _palette_mode_from_signals(
    signals: str, extraction: ExtractionSnapshot
) -> tuple[PaletteMode, str]:
    color_text = " ".join(
        f"{cue.label} {cue.value} {cue.note or ''}"
        for cue in extraction.brandAssetCues
        if cue.assetType == "color"
    ).lower()
    if _contains_any(
        color_text or signals,
        ["vibrant", "bright", "gradient", "multi", "colorful", "bold"],
    ):
        return (
            "colorful",
            "The source brand cues contain enough color energy to support a more expressive palette.",
        )
    if _contains_any(
        color_text or signals,
        [
            "monochrome",
            "neutral",
            "minimal",
            "zinc",
            "grayscale",
            "grey",
            "gray",
            "black",
            "white",
        ],
    ):
        return (
            "zinc",
            "The source site reads as restrained and neutral, so a zinc palette keeps the preview aligned.",
        )
    if _contains_any(
        signals, ["premium", "advisory", "enterprise", "clean", "refined"]
    ):
        return (
            "light",
            "The source language suggests a clean, premium treatment without pushing into a dark monochrome system.",
        )
    return (
        "light",
        "No strong chromatic cues were available, so the preview stays in a light palette with explicit inference labels.",
    )


def _confidence(*scores: int, floor: int = 0, ceiling: int = 95) -> int:
    values = [int(score) for score in scores if score is not None]
    if not values:
        return floor
    return max(floor, min(ceiling, round(sum(values) / len(values))))


def _site_refs(
    brief: SiteBrief, extraction: ExtractionSnapshot
) -> list[dict[str, Any]]:
    refs = [
        _page_reference_from_citation(citation.model_dump())
        for citation in extraction.sourceCitations
    ]
    refs.extend(
        _asset_reference_from_cue(cue.model_dump()) for cue in extraction.brandAssetCues
    )
    refs.extend(citation.model_dump() for citation in brief.sourceCitations)
    return _dedupe_refs(refs)


def _brand_tokens(
    *,
    palette_mode: PaletteMode,
    theme: dict[str, Any],
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    refs: list[dict[str, Any]],
    industry: str | None = None,
) -> dict[str, Any]:
    color_cues = [
        cue.model_dump()
        for cue in extraction.brandAssetCues
        if cue.assetType == "color"
    ]
    logo_cues = [
        cue.model_dump() for cue in extraction.brandAssetCues if cue.assetType == "logo"
    ]
    typography_cues = [
        cue.model_dump()
        for cue in extraction.brandAssetCues
        if cue.assetType == "typography"
    ]
    image_cues = [
        cue.model_dump()
        for cue in extraction.brandAssetCues
        if cue.assetType == "image"
    ]
    tone_text = " ".join(extraction.summary.toneClues[:3]) or _text(
        brief.toneProfile.value
    )
    source_refs = refs[:4]
    color_reference = source_refs[:2] or refs[:1]
    palette_defaults = {
        "zinc": {
            "background": "#0b0f14",
            "text": "#f8fafc",
            "border": "#253040",
            "accent": "#94a3b8",
        },
        "light": {
            "background": "#f8fafc",
            "text": "#0f172a",
            "border": "#dbe4f0",
            "accent": "#334155",
        },
        "colorful": {
            "background": "#08111f",
            "text": "#eff6ff",
            "border": "#1f2d4a",
            "accent": "#f97316",
        },
    }[palette_mode]

    # Extract source colors for enhanced color system generation
    source_colors = []
    if color_cues:
        for cue in color_cues[:3]:
            color_val = _text(cue["value"])
            if color_val and color_val.startswith("#"):
                source_colors.append(color_val)

    # Detect industry design config mood
    # Map to valid industry for color system (narrower type than industry_detection)
    valid_industries = {
        "creative_agency",
        "saas",
        "legal_finance",
        "ecommerce_fashion",
        "consulting",
        "real_estate",
        "health_wellness",
        "tech",
    }
    industry_for_config = (
        cast(Any, industry) if industry in valid_industries else "tech"
    )
    industry_config = (
        get_industry_design_config(industry_for_config) if industry else {}
    )
    mood = industry_config.get("color_palette_mood", "professional")
    dark_mode = palette_mode != "light"

    # Generate enhanced color system
    try:
        color_system = generate_color_system(
            source_colors=source_colors,
            industry=cast(Any, industry) if industry in valid_industries else "tech",
            mood=mood,
            dark_mode=dark_mode,
        )
    except Exception as e:
        logger.warning(f"Color system generation failed, using defaults: {e}")
        color_system = None

    # Use enhanced color system if available, otherwise fall back to original logic
    if color_system:
        primary_value = color_system["primary"]
        secondary_value = color_system["secondary"]
        accent_value = color_system["accent"]
        primary_refs = (
            [_asset_reference_from_cue(color_cues[0])]
            if color_cues
            else color_reference
        )
        secondary_refs = (
            [_asset_reference_from_cue(color_cues[1])]
            if len(color_cues) > 1
            else color_reference
        )
        accent_refs = (
            [_asset_reference_from_cue(color_cues[2])]
            if len(color_cues) > 2
            else color_reference
        )
    elif color_cues:
        first = color_cues[0]
        primary_value = _text(first["value"])
        primary_refs = [_asset_reference_from_cue(first)]
        if len(color_cues) > 1:
            secondary_value = _text(color_cues[1]["value"])
            secondary_refs = [_asset_reference_from_cue(color_cues[1])]
        else:
            secondary_value = palette_defaults["accent"]
            secondary_refs = color_reference
        accent_value = (
            _text(color_cues[2]["value"])
            if len(color_cues) > 2
            else palette_defaults["accent"]
        )
        accent_refs = (
            [_asset_reference_from_cue(color_cues[2])]
            if len(color_cues) > 2
            else color_reference
        )
    else:
        primary_value = (
            palette_defaults["accent"] if palette_mode == "colorful" else "#475569"
        )
        secondary_value = "#94a3b8" if palette_mode == "zinc" else "#64748b"
        accent_value = palette_defaults["accent"]
        primary_refs = color_reference
        secondary_refs = color_reference
        accent_refs = color_reference

    logo_value = logo_cues[0]["label"] if logo_cues else "No logo asset captured"
    logo_kind = "source_backed" if logo_cues else "inferred"
    logo_refs = (
        [_asset_reference_from_cue(cue) for cue in logo_cues] if logo_cues else refs[:1]
    )
    typography_value = (
        typography_cues[0]["value"]
        if typography_cues
        else str(theme["typographyPairing"])
    )
    typography_kind = "source_backed" if typography_cues else "inferred"
    typography_refs = (
        [_asset_reference_from_cue(typography_cues[0])] if typography_cues else refs[:2]
    )
    image_value = (
        image_cues[0]["label"] if image_cues else "No image direction captured"
    )
    image_kind = "source_backed" if image_cues else "inferred"
    image_refs = (
        [_asset_reference_from_cue(cue) for cue in image_cues]
        if image_cues
        else refs[:2]
    )
    visual_tone_value = tone_text or brief.toneProfile.value
    visual_tone_kind = "source_backed" if extraction.summary.toneClues else "inferred"
    visual_tone_refs = refs[:3]
    motion_value = str(theme["motionPreset"])
    motion_kind = "inferred"
    layout_value = str(theme["spacingStyle"])
    layout_kind = "inferred"
    return {
        "paletteMode": palette_mode,
        "primaryColor": _token(
            str(primary_value),
            source_kind="source_backed" if color_cues else "inferred",
            inference_label="Taken directly from extracted brand color cues."
            if color_cues
            else "Derived from the selected palette and theme.",
            confidence=_confidence(
                *(cue["confidence"] for cue in color_cues[:2]),
                floor=55 if color_cues else 36,
            ),
            references=primary_refs,
        ),
        "secondaryColor": _token(
            str(secondary_value),
            source_kind="source_backed" if len(color_cues) > 1 else "inferred",
            inference_label="Taken from the second captured brand color."
            if len(color_cues) > 1
            else "Derived from the selected palette and theme.",
            confidence=_confidence(
                *(cue["confidence"] for cue in color_cues[1:3]),
                floor=52 if len(color_cues) > 1 else 34,
            ),
            references=secondary_refs,
        ),
        "accentColor": _token(
            str(accent_value),
            source_kind="source_backed" if len(color_cues) > 2 else "inferred",
            inference_label="Taken from the extracted accent color cue."
            if len(color_cues) > 2
            else "Derived from the palette mode and theme direction.",
            confidence=_confidence(
                *(cue["confidence"] for cue in color_cues[2:3]),
                floor=50 if len(color_cues) > 2 else 34,
            ),
            references=accent_refs,
        ),
        "backgroundColor": _token(
            palette_defaults["background"],
            source_kind="inferred",
            inference_label="Chosen to fit the selected palette mode.",
            confidence=68,
            references=refs[:2],
        ),
        "textColor": _token(
            palette_defaults["text"],
            source_kind="inferred",
            inference_label="Chosen to keep contrast readable in the selected palette mode.",
            confidence=68,
            references=refs[:2],
        ),
        "borderColor": _token(
            palette_defaults["border"],
            source_kind="inferred",
            inference_label="Chosen to keep the section framing legible without filling the page with decorative chrome.",
            confidence=65,
            references=refs[:2],
        ),
        "logoAsset": _token(
            logo_value,
            source_kind=logo_kind,
            inference_label="Captured from the public logo asset."
            if logo_cues
            else "No logo asset was captured, so the preview marks the gap explicitly.",
            confidence=_confidence(
                *(cue["confidence"] for cue in logo_cues[:1]),
                floor=40 if logo_cues else 20,
            ),
            references=logo_refs,
        ),
        "typography": _token(
            typography_value,
            source_kind=typography_kind,
            inference_label="Captured from the public typography cue."
            if typography_cues
            else "Derived from the selected theme pairing because the source typography cue was sparse.",
            confidence=_confidence(
                *(cue["confidence"] for cue in typography_cues[:1]),
                floor=42 if typography_cues else 28,
            ),
            references=typography_refs,
        ),
        "imageStyle": _token(
            image_value,
            source_kind=image_kind,
            inference_label="Captured from the public image cue."
            if image_cues
            else "Derived from the source visual language because no clear image direction was extracted.",
            confidence=_confidence(
                *(cue["confidence"] for cue in image_cues[:1]),
                floor=38 if image_cues else 24,
            ),
            references=image_refs,
        ),
        "visualTone": _token(
            visual_tone_value,
            source_kind=visual_tone_kind,
            inference_label="Taken from the extraction tone cues."
            if extraction.summary.toneClues
            else "Derived from the approved brief tone profile.",
            confidence=_confidence(
                *(citation["confidence"] for citation in refs[:3]),
                floor=54 if extraction.summary.toneClues else 30,
            ),
            references=visual_tone_refs,
        ),
        "motionIntensity": _token(
            motion_value,
            source_kind=motion_kind,
            inference_label="Selected from the theme motion preset.",
            confidence=70,
            references=refs[:2],
        ),
        "layoutDensity": _token(
            layout_value,
            source_kind=layout_kind,
            inference_label="Selected from the theme spacing style.",
            confidence=70,
            references=refs[:2],
        ),
        # Enhanced color system fields
        "enhancedColorSystem": color_system if color_system else {},
    }


def _hero_variant(
    *,
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    theme: dict[str, Any],
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    # Build a polished, visitor-facing headline from brief + extraction.
    raw_hero = _strip_instruction_leads(brief.recommendedHero.value)
    company_summary = _strip_instruction_leads(brief.companySummary.value)
    positioning = _strip_instruction_leads(extraction.summary.positioningSummary or "")

    # Collect basic identity signals from pageInventory (home and key pages).
    homepage_title: str | None = None
    meta_description: str | None = None
    primary_h1: str | None = None
    for page in getattr(extraction, "pageInventory", []) or []:
        page_data = page.model_dump() if hasattr(page, "model_dump") else page
        # Prefer homepage and shallow pages
        if page_data.get("source") == "homepage" or page_data.get("depth", 99) <= 1:
            title = _text(page_data.get("title"))
            if title and not homepage_title:
                homepage_title = title
            description = _text((page_data.get("meta") or {}).get("description"))
            if description and not meta_description:
                meta_description = description
            headings = page_data.get("headings") or []
            if headings and not primary_h1:
                primary_h1 = _text(headings[0])

    # Drop obviously operator-facing candidates so we never surface
    # "Brand cues", "Conversion path", etc. in the public hero.
    if _looks_operator_facing(raw_hero):
        raw_hero = ""
    if _looks_operator_facing(company_summary):
        company_summary = ""
    if _looks_operator_facing(positioning):
        positioning = ""

    # Look for a mission-style sentence in high-confidence sections across
    # all crawled pages (about/hero sections, or sections mentioning mission).
    section_mission: str | None = None
    try:
        best_score = 0
        for section in getattr(extraction, "sectionInventory", []) or []:
            data = section.model_dump() if hasattr(section, "model_dump") else section
            text_blob = _text(data.get("text") or data.get("heading"))
            if not text_blob:
                continue
            kind = _text(data.get("type")).lower()
            section_conf = int(data.get("confidence") or 0)
            score = section_conf
            if kind in {"about", "hero"}:
                score += 12
            elif kind in {"services", "proof"}:
                score += 6
            lowered = text_blob.lower()
            if any(term in lowered for term in ["mission", "our story", "who we are"]):
                score += 10
            if score <= best_score:
                continue
            # Use the first sentence as a mission-style snippet
            snippet = re.split(r"[.!?\n]", text_blob)[0].strip()
            snippet = _sanitize_public_copy(snippet)
            if not snippet or _looks_operator_facing(snippet):
                continue
            best_score = score
            section_mission = snippet
    except Exception:
        section_mission = section_mission or None

    headline_candidate = (
        raw_hero
        or company_summary
        or section_mission
        or primary_h1
        or homepage_title
        or positioning
    )
    if headline_candidate:
        headline_source = _compress_mission_line(headline_candidate)
    else:
        headline_source = ""

    if not headline_source:
        # Construct a neutral benefit-driven headline from service clues
        headline_source = _compose_benefit_headline(
            extraction
        ) or _sanitize_public_copy("Make work more organized and clear")

    # Prepend brand name when we have it and it is not already present.
    brand_name = _text(extraction.summary.companyName)
    if brand_name:
        lowered_headline = headline_source.lower()
        if brand_name.lower() not in lowered_headline:
            headline_source = _sanitize_public_copy(f"{brand_name}: {headline_source}")

    # Supporting and subheadline copy without internal terms
    supporting_candidate = (
        _strip_instruction_leads(brief.valuePropositionSummary.value)
        or meta_description
        or positioning
        or company_summary
        or section_mission
        or headline_source
    )
    if _looks_operator_facing(supporting_candidate):
        supporting_candidate = section_mission or headline_source
    # Avoid meta instructions like "Make the CTA pattern explicit".
    if re.search(
        r"make\b[^.]{0,80}\bcta pattern\b", supporting_candidate, flags=re.IGNORECASE
    ):
        supporting_candidate = (
            section_mission or meta_description or company_summary or headline_source
        )
    supporting = _sanitize_public_copy(supporting_candidate)
    subheadline = _sanitize_public_copy(
        _strip_instruction_leads(brief.audienceHypothesis.value)
    )

    # Prefer client-facing CTA verbs; fall back to safe defaults
    cta_hint = _text(brief.conversionAngle.value) or ""
    if _contains_any(cta_hint, ["trial", "start", "sign up", "get started", "try"]):
        primary_cta = _ensure_client_safe_cta("Start your trial")
        secondary_cta = _ensure_client_safe_cta("See how it works")
    elif _contains_any(cta_hint, ["book", "demo", "call", "consult"]):
        primary_cta = _ensure_client_safe_cta("See how it works")
        secondary_cta = _ensure_client_safe_cta("Contact us")
    elif _contains_any(cta_hint, ["contact", "quote", "estimate", "inquiry"]):
        primary_cta = _ensure_client_safe_cta("Contact us")
        secondary_cta = _ensure_client_safe_cta("Learn more")
    else:
        primary_cta = _ensure_client_safe_cta("See how it works")
        secondary_cta = _ensure_client_safe_cta("Learn more")

    return {
        "headline": headline_source,
        "subheadline": subheadline,
        "supportingLine": supporting,
        "primaryCta": primary_cta,
        "secondaryCta": secondary_cta,
        "layout": theme["heroFamily"],
        "visualTreatment": theme["colorTreatment"],
        "evidence": _brief_evidence(
            source_kind="source_backed" if brief.recommendedHero.value else "inferred",
            inference_label="Derived from approved content and site signals",
            confidence=_confidence(
                brief.recommendedHero.evidence.confidence,
                brief.conversionAngle.evidence.confidence,
                floor=48,
            ),
            references=refs[:3],
        ),
    }


def _map_section_kind_to_component_id(kind: str) -> str:
    """Map a section kind/label to a premium component ID.

    Uses broad keyword matching so it can handle both canonical kinds
    ("services", "proof", etc.) and more free-form labels.
    """
    value = _text(kind).lower()
    if not value:
        return "services-bento"

    # Stats / metrics / numbers
    if any(
        token in value
        for token in ["stat", "metric", "number", "count", "achievement", "result"]
    ):
        return "stats-counter"

    # Services / offerings / capabilities - prefer interactive
    if any(
        token in value for token in ["service", "offering", "feature", "capability"]
    ):
        return "services-tabs"

    # Proof / testimonials / results / social proof
    if any(
        token in value
        for token in [
            "proof",
            "testimonial",
            "review",
            "highlight",
            "case",
            "trust",
            "social",
        ]
    ):
        return "proof-carousel"

    # Process / methodology / timeline
    if any(
        token in value
        for token in [
            "process",
            "method",
            "approach",
            "step",
            "workflow",
            "timeline",
        ]
    ):
        return "timeline-vertical"

    # Gallery / portfolio / work showcase
    if any(
        token in value
        for token in [
            "gallery",
            "portfolio",
            "work",
            "project",
            "showcase",
        ]
    ):
        return "gallery-masonry"

    # About / story / vision
    if any(
        token in value
        for token in [
            "about",
            "story",
            "point of view",
            "vision",
            "mission",
        ]
    ):
        return "editorial-feature"

    # Comparison / plans
    if any(
        token in value for token in ["comparison", "compare", "versus", "vs", "plan"]
    ):
        return "features-comparison"

    # CTA / contact / booking / pricing
    if any(
        token in value
        for token in [
            "cta",
            "contact",
            "book",
            "schedule",
            "quote",
            "pricing",
        ]
    ):
        return "cta-banner"

    # Default safe fallback - interactive bento
    return "services-bento"


def _section_stack(
    *,
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    company_summary = _strip_instruction_leads(brief.companySummary.value)
    positioning = _strip_instruction_leads(extraction.summary.positioningSummary or "")
    section_refs = refs[:4]

    page_refs = [r for r in refs if r.get("kind") == "page" and r.get("excerpt")]
    source_sections = [
        section.model_dump() if hasattr(section, "model_dump") else section
        for section in getattr(extraction, "sectionInventory", [])
    ]

    # Build an index of pages and score sections so we can favor
    # high-confidence, shallower-depth content (including inner pages)
    # when selecting body copy for each section kind.
    page_by_url: dict[str, dict[str, Any]] = {}
    for page in getattr(extraction, "pageInventory", []) or []:
        page_data = page.model_dump() if hasattr(page, "model_dump") else page
        url = page_data.get("url")
        if url:
            page_by_url[url] = page_data

    section_candidates_by_kind: dict[str, list[dict[str, Any]]] = {}
    for section in source_sections:
        kind = _text(section.get("type")).lower()
        if not kind:
            continue
        page_meta = page_by_url.get(section.get("pageUrl") or "")
        depth = int(page_meta.get("depth", 0)) if page_meta else 0
        page_conf = int(page_meta.get("confidence", 0)) if page_meta else 0
        section_conf = int(section.get("confidence") or 0)
        score = section_conf + page_conf // 2
        # Prefer shallower pages but still allow rich inner pages to surface
        score += max(0, 6 - depth * 2)
        text_blob = (
            f"{_text(section.get('heading'))} {_text(section.get('text'))}".lower()
        )
        if any(term in text_blob for term in ["mission", "our story", "who we are"]):
            score += 10
        if any(
            term in text_blob
            for term in ["support", "donate", "apply", "volunteer", "contact", "visit"]
        ):
            score += 6
        section["_score"] = score
        section_candidates_by_kind.setdefault(kind, []).append(section)

    for kind, candidates in section_candidates_by_kind.items():
        candidates.sort(key=lambda s: s.get("_score", 0), reverse=True)

    def get_related_excerpts(topic: str, max_count: int = 2) -> list[str]:
        topic_words = {w for w in re.findall(r"\w+", topic.lower()) if len(w) > 3}
        if not topic_words:
            return []
        matches = []
        for r in page_refs:
            excerpt = r["excerpt"]
            if any(w in excerpt.lower() for w in topic_words):
                if excerpt not in matches:
                    matches.append(excerpt)
        return matches[:max_count]

    if hasattr(brief, "visualRedesign") and brief.visualRedesign:
        for page in brief.visualRedesign:
            for critique in page.critiques:
                section_kind = critique.sectionType
                if section_kind == "hero":
                    continue  # handled by hero variant
                title = section_kind.capitalize()
                sections.append(
                    {
                        "kind": section_kind,
                        "title": title,
                        "eyebrow": None,
                        "headline": title,
                        "body": _sanitize_public_copy(
                            " ".join(critique.contentToReuse)
                        ),
                        "items": [],
                        "ctaLabel": None,
                        "componentId": critique.recommendedComponent,
                        "evidence": _brief_evidence(
                            source_kind="source_backed",
                            inference_label="Generated from Visual Critique redesign plan.",
                            confidence=critique.confidence,
                            references=section_refs,
                        ),
                    }
                )
    elif brief.recommendedSections:
        META_TITLES = {
            "hero",
            "cta",
            "call to action",
            "brand",
            "audience",
            "conversion",
        }
        for _index, recommendation in enumerate(brief.recommendedSections[:8], start=1):
            title = (
                _strip_instruction_leads(recommendation.title) or recommendation.title
            )
            lowered = title.strip().lower()
            # Drop obviously operator/meta sections that are not visitor-facing.
            if lowered in META_TITLES:
                continue
            if any(
                phrase in lowered
                for phrase in [
                    "open question",
                    "open questions",
                    "missing requirement",
                    "gap item",
                    "gap items",
                    "source cues",
                    "extraction",
                    "operator review",
                ]
            ):
                continue
            items: list[str] = []
            section_kind = "section"
            display_title = title
            forced_section_kind: str | None = None
            if "brand cues" in lowered:
                display_title = "Our identity"
                forced_section_kind = "about"
            elif "conversion path" in lowered or "cta pattern" in lowered:
                display_title = "How to get in touch"
                forced_section_kind = "contact"
            elif "highlights" in lowered and "work" not in lowered:
                display_title = "Highlights from our work"
                forced_section_kind = "proof"

            if forced_section_kind is not None:
                section_kind = forced_section_kind
            if forced_section_kind is None:
                if "service" in lowered or "offering" in lowered:
                    section_kind = "services"
                elif "proof" in lowered or "trust" in lowered or "highlight" in lowered:
                    section_kind = "proof"
                elif "process" in lowered or "method" in lowered:
                    section_kind = "process"
                elif "pricing" in lowered or "package" in lowered:
                    section_kind = "pricing"
                elif "gallery" in lowered or "work" in lowered:
                    section_kind = "gallery"
                elif "contact" in lowered:
                    section_kind = "contact"
                elif "about" in lowered or "point of view" in lowered:
                    section_kind = "about"

            # Map section kinds to premium component IDs for fallback
            component_id = _map_section_kind_to_component_id(section_kind)

            related_excerpts = get_related_excerpts(title, max_count=4)
            matching_source_sections = (
                section_candidates_by_kind.get(section_kind, [])
                if section_kind != "section"
                else []
            )
            source_excerpt = _sanitize_public_copy(
                _text(matching_source_sections[0].get("text"))
                if matching_source_sections
                else ""
            )
            body_text = _sanitize_public_copy(
                recommendation.rationale or company_summary or positioning
            )
            if source_excerpt:
                body_text = source_excerpt[:520]
            elif related_excerpts and not (
                "service" in lowered or "offering" in lowered or "audience" in lowered
            ):
                body_text = _sanitize_public_copy(related_excerpts[0])

            if section_kind == "services":
                base_items = [
                    s for s in (extraction.summary.serviceClues or []) if _text(s)
                ]
                source_items = [
                    _text(section.get("heading"))
                    for section in matching_source_sections
                    if _text(section.get("heading"))
                ]
                items = (base_items + source_items + related_excerpts)[:6]
            elif section_kind in {
                "proof",
                "process",
                "pricing",
                "gallery",
                "about",
                "contact",
            }:
                source_items = [
                    _sanitize_public_copy(
                        _text(section.get("heading"))
                        or _text(section.get("text"))[:160]
                    )
                    for section in matching_source_sections[:6]
                ]
                items = (source_items + related_excerpts[1:3])[:6]
            elif "audience" in lowered:
                base_items = [
                    a for a in (extraction.summary.audienceClues or []) if _text(a)
                ]
                items = (base_items + related_excerpts)[:6]
            elif related_excerpts and len(related_excerpts) > 1:
                items = related_excerpts[1:3]

            sections.append(
                {
                    "kind": section_kind,
                    "title": display_title,
                    "eyebrow": None,
                    "headline": display_title,
                    "body": body_text,
                    "items": [_sanitize_public_copy(i) for i in items],
                    "ctaLabel": None,
                    "componentId": component_id,
                    "evidence": recommendation.evidence.model_dump()
                    if hasattr(recommendation.evidence, "model_dump")
                    else recommendation.evidence,
                }
            )
    else:
        # Provide a neutral, client-facing fallback section instead of an operator gap
        services = [s for s in (extraction.summary.serviceClues or []) if s]
        audience = [a for a in (extraction.summary.audienceClues or []) if a]
        fallback_headline_source = positioning or company_summary
        if not fallback_headline_source:
            # Last-resort headline that still reads client-facing instead of as
            # an obvious placeholder.
            fallback_headline_source = _sanitize_public_copy("About this company")
        sections.append(
            {
                "kind": "section",
                "title": "Overview",
                "eyebrow": None,
                "headline": _sanitize_public_copy(fallback_headline_source),
                "body": _sanitize_public_copy(
                    "\n".join(
                        filter(
                            None,
                            [
                                company_summary,
                                positioning,
                            ],
                        )
                    )
                ),
                "items": (services[:3] or audience[:3]),
                "ctaLabel": None,
                "componentId": _map_section_kind_to_component_id("overview"),
                "evidence": _brief_evidence(
                    source_kind="inferred",
                    inference_label="Public-safe summary grounded in extracted positioning where available.",
                    confidence=52,
                    references=section_refs,
                ),
            }
        )

    # Append a proof/highlights section only if we don't already have a proof-like
    # section in this stack.
    existing_kinds = {
        _canonical_section_type(section.get("kind") or section.get("title") or "")
        or section.get("kind")
        for section in sections
    }

    proof_points = list(brief.proofPoints[:3])
    if proof_points and "proof" not in existing_kinds:
        sections.append(
            {
                "kind": "proof",
                "title": "Highlights",
                "eyebrow": None,
                "headline": "Highlights",
                "body": _sanitize_public_copy(
                    "A few highlights drawn directly from approved source content."
                ),
                "items": [f"{proof.label}: {proof.detail}" for proof in proof_points],
                "ctaLabel": None,
                "componentId": _map_section_kind_to_component_id("proof"),
                "evidence": _brief_evidence(
                    source_kind="source_backed",
                    inference_label="Highlights are drawn from approved source content.",
                    confidence=_confidence(
                        *(proof.evidence.confidence for proof in proof_points),
                        floor=58,
                    ),
                    references=section_refs,
                ),
            }
        )

    # Append a CTA section only if there isn't already a CTA/contact-style
    # section present. Ground the body copy in the approved conversion angle
    # or positioning summary when available.
    if "cta" not in existing_kinds and "contact" not in existing_kinds:
        cta_body_source = _strip_instruction_leads(brief.conversionAngle.value) or (
            positioning or company_summary
        )
        if not cta_body_source:
            cta_body_source = (
                "Explore the details and decide if this is a fit for your team."
            )

        sections.append(
            {
                "kind": "cta",
                "title": "Get started",
                "eyebrow": None,
                "headline": _sanitize_public_copy(
                    _strip_instruction_leads(brief.conversionAngle.value)
                    or "Ready to take the next step?"
                ),
                "body": _sanitize_public_copy(cta_body_source),
                "items": [],
                "ctaLabel": _ensure_client_safe_cta("See how it works"),
                "componentId": _map_section_kind_to_component_id("cta"),
                "evidence": _brief_evidence(
                    source_kind="source_backed"
                    if brief.conversionAngle.value
                    else "inferred",
                    inference_label="CTA derived from approved conversion angle where available.",
                    confidence=_confidence(
                        brief.conversionAngle.evidence.confidence, floor=52
                    ),
                    references=section_refs[:2],
                ),
            }
        )

    # Deduplicate sections by title to prevent excessive duplication
    # This prevents the quality score from being set to 0 due to >40% duplicates
    seen_titles: set[str] = set()
    deduplicated_sections: list[dict[str, Any]] = []

    for section in sections:
        title_key = _text(section.get("title", "")).strip().lower()
        if not title_key:
            # Keep sections without titles (shouldn't happen but defensive)
            deduplicated_sections.append(section)
            continue

        if title_key in seen_titles:
            # Skip duplicate section
            logger.debug(f"Skipping duplicate section with title: {title_key}")
            continue

        seen_titles.add(title_key)
        deduplicated_sections.append(section)

    if len(deduplicated_sections) < len(sections):
        logger.info(
            f"Deduplicated sections from {len(sections)} to {len(deduplicated_sections)} "
            f"({len(sections) - len(deduplicated_sections)} duplicates removed)"
        )

    return deduplicated_sections


def _canonical_section_type(label: str) -> str | None:
    value = _text(label).lower()
    if not value:
        return None
    if "hero" in value:
        return "hero"
    if "service" in value or "offering" in value:
        return "services"
    if "proof" in value or "testimonial" in value or "trust" in value:
        return "proof"
    if "process" in value or "timeline" in value or "method" in value:
        return "process"
    if "pricing" in value or "package" in value:
        return "pricing"
    if "gallery" in value or "work" in value or "portfolio" in value:
        return "gallery"
    if "about" in value or "story" in value:
        return "about"
    if "contact" in value or "reach" in value:
        return "contact"
    if "cta" in value or "call to action" in value:
        return "cta"
    return value


def _auto_component_for_section_type(section_type: str) -> str | None:
    """Select a premium componentId for a canonical section type.

    This is used for automatic refinements based on screenshot QA
    improvement briefs and intentionally only returns componentIds
    that are registered in the premium frontend registry.
    """

    key = (section_type or "").lower()
    if not key:
        return None
    if key == "hero":
        return "hero-split-editorial"
    if key == "services":
        return "services-bento"
    if key == "proof":
        return "proof-carousel"
    if key in {"process", "timeline"}:
        return "timeline-vertical"
    if key == "gallery":
        return "gallery-masonry"
    if key in {"about", "pricing"}:
        return "editorial-feature"
    if key in {"cta", "contact"}:
        return "cta-banner"
    return None


def _auto_refinement_from_improvement_brief(
    improvement: dict[str, Any] | None,
) -> dict[str, Any]:
    """Convert a screenshot improvement brief into refinement hints.

    The output shape matches what _apply_refinement_to_visual_redesign
    expects: a dict with a "componentSuggestions" list and optional
    "visualTone" string. This keeps automatic iteration lightweight
    and client-safe while still nudging section layouts toward
    premium components.
    """

    if not improvement:
        return {"componentSuggestions": []}

    section_improvements = improvement.get("sectionImprovements") or []
    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in section_improvements:
        title = _text(item.get("sectionTitle"))
        if not title:
            continue
        canonical = _canonical_section_type(title) or title
        component_id = _auto_component_for_section_type(canonical)
        if not component_id:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        suggestions.append({"section": canonical, "suggestedComponent": component_id})

    visual_tone: str | None = None
    overall = _text(improvement.get("overallApproach"))
    if overall:
        lowered = overall.lower()
        if "editorial" in lowered:
            visual_tone = "editorial-frame"
        elif "minimal" in lowered or "clean" in lowered:
            visual_tone = "minimal-luxe"

    result: dict[str, Any] = {"componentSuggestions": suggestions}
    if visual_tone:
        result["visualTone"] = visual_tone
    return result


def _apply_refinement_to_visual_redesign(
    *, brief: SiteBrief, refinement: dict[str, Any]
) -> list[VisualRedesignBrief]:
    suggestions = refinement.get("componentSuggestions") or []
    if not getattr(brief, "visualRedesign", None) or not suggestions:
        return list(getattr(brief, "visualRedesign", []) or [])

    mapping: dict[str, str] = {}
    for item in suggestions:
        section_label = _canonical_section_type(item.get("section", ""))
        component_id = _text(item.get("suggestedComponent"))
        if section_label and component_id:
            mapping[section_label] = component_id

    if not mapping:
        return list(brief.visualRedesign)

    updated_pages: list[VisualRedesignBrief] = []
    visual_tone = _text(refinement.get("visualTone"))

    for page in brief.visualRedesign:
        updated_critiques: list[VisualCritique] = []
        for critique in page.critiques:
            section_type_key = (
                _canonical_section_type(critique.sectionType) or critique.sectionType
            )
            suggested_component = mapping.get(section_type_key)
            if suggested_component:
                critique = critique.model_copy(
                    update={"recommendedComponent": suggested_component}
                )
            updated_critiques.append(critique)

        art_direction = visual_tone or page.artDirection
        updated_pages.append(
            VisualRedesignBrief(
                pageUrl=page.pageUrl,
                critiques=updated_critiques,
                artDirection=art_direction,
            )
        )

    return updated_pages


def _cta_strategy(
    brief: SiteBrief, extraction: ExtractionSnapshot, refs: list[dict[str, Any]]
) -> dict[str, Any]:
    primary = "See how it works"
    secondary = "Learn more"
    footer = "Contact us"
    rationale = (
        _text(brief.conversionAngle.value)
        or "Conversion angle not explicit; using a safe default."
    )
    if _contains_any(rationale, ["quote", "estimate", "proposal"]):
        primary = "Request a quote"
        secondary = "Learn more"
        footer = "Contact us"
    elif _contains_any(rationale, ["book", "call", "meeting", "demo", "consult"]):
        primary = "See how it works"
        secondary = "Contact us"
        footer = "Contact us"
    elif _contains_any(rationale, ["learn", "discover", "explore"]):
        primary = "See how it works"
        secondary = "Learn more"
        footer = "Contact us"
    return {
        "primary": _brief_action(
            _ensure_client_safe_cta(primary),
            "#contact",
            rationale,
            refs[:2],
            brief.conversionAngle.evidence.confidence,
        ),
        "secondary": _brief_action(
            _ensure_client_safe_cta(secondary),
            "#sections",
            "Offer a lower-friction path for exploration.",
            refs[:2],
            max(brief.conversionAngle.evidence.confidence - 10, 40),
        ),
        "footer": _brief_action(
            _ensure_client_safe_cta(footer),
            "#contact",
            "Provide a clear contact path for interested visitors.",
            refs[:2],
            58,
        ),
    }


def _brief_action(
    label: str, href: str, rationale: str, refs: list[dict[str, Any]], confidence: int
) -> dict[str, Any]:
    return {
        "label": label,
        "href": href,
        "rationale": rationale,
        "evidence": _brief_evidence(
            source_kind="inferred" if href.startswith("#") else "source_backed",
            inference_label=rationale,
            confidence=confidence,
            references=refs,
        ),
    }


def _review_rubric(
    *,
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    site_sections: list[dict[str, Any]],
    brand_tokens: dict[str, Any],
    palette_mode: PaletteMode,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    has_placeholders = any(
        "lorem ipsum" in _text(section["body"]).lower()
        or "fake" in _text(section["body"]).lower()
        or "placeholder" in _text(section["body"]).lower()
        for section in site_sections
    )
    checks.append(
        {
            "key": "placeholder_free",
            "label": "Placeholder-free preview",
            "status": "pass" if not has_placeholders else "fail",
            "notes": "No placeholder copy, fake metrics, or demo filler is present in the generated sections."
            if not has_placeholders
            else "The generated output contains placeholder-like language and should not be published.",
            "evidence": None,
        }
    )
    traceable_tokens = [
        brand_tokens["primaryColor"],
        brand_tokens["accentColor"],
        brand_tokens["typography"],
    ]
    checks.append(
        {
            "key": "brand_traceability",
            "label": "Brand traceability",
            "status": "pass"
            if any(
                token["evidence"]["sourceKind"] == "source_backed"
                for token in traceable_tokens
            )
            else "warn",
            "notes": "At least one of the core brand tokens is grounded in extracted source cues."
            if any(
                token["evidence"]["sourceKind"] == "source_backed"
                for token in traceable_tokens
            )
            else "Brand tokens are mostly inferred because the source cues were sparse.",
            "evidence": traceable_tokens[0]["evidence"],
        }
    )
    checks.append(
        {
            "key": "palette_fit",
            "label": "Palette mode fit",
            "status": "pass"
            if palette_mode in {"zinc", "light", "colorful"}
            else "fail",
            "notes": f"The preview uses the {palette_mode} palette because the source visual language supported it.",
            "evidence": brand_tokens["backgroundColor"]["evidence"],
        }
    )
    checks.append(
        {
            "key": "cta_clarity",
            "label": "CTA clarity",
            "status": "pass" if _text(brief.conversionAngle.value) else "warn",
            "notes": "A primary CTA and a lower-friction secondary CTA are visible in the preview."
            if _text(brief.conversionAngle.value)
            else "The conversion angle is too sparse to fully validate the CTA plan.",
            "evidence": brief.conversionAngle.evidence.model_dump()
            if hasattr(brief.conversionAngle.evidence, "model_dump")
            else brief.conversionAngle.evidence,
        }
    )
    checks.append(
        {
            "key": "screenshot_ready",
            "label": "Screenshot QA ready",
            "status": "warn" if extraction.confidenceScore < 60 else "pass",
            "notes": "The preview can be reviewed in-browser and captured for visual QA; low-confidence sources should be inspected before publish.",
            "evidence": brief.conversionAngle.evidence.model_dump()
            if hasattr(brief.conversionAngle.evidence, "model_dump")
            else brief.conversionAngle.evidence,
        }
    )
    return checks


def _quality_score(
    *,
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    brand_tokens: dict[str, Any],
    site_sections: list[dict[str, Any]],
    missing_requirements: list[str],
    diversity_score: int = 50,
    screenshot_qa_score: int | None = None,
) -> int:
    """Compute overall quality score with an emphasis on visual design quality.

    Visual quality is primary when screenshot QA is available, but we enforce
    hard guards so obviously broken designs (no premium components, repeated
    sections) cannot receive high scores.
    """

    # DESIGN QUALITY CHECKS
    if site_sections:
        sections_with_component_id = sum(
            1 for s in site_sections if s.get("componentId")
        )
        total_sections = len(site_sections)

        # No premium components at all – automatic fail
        if sections_with_component_id == 0:
            logger.warning(
                "No sections have componentId set. Returning quality score of 0."
            )
            return 0

        # If fewer than half the sections have componentIds, cap visual score
        if sections_with_component_id < total_sections * 0.5:
            logger.warning(
                "Only %s/%s sections have componentId. Capping screenshot QA contribution at 30.",
                sections_with_component_id,
                total_sections,
            )
            if screenshot_qa_score is not None:
                screenshot_qa_score = min(screenshot_qa_score, 30)

        # Detect excessive section duplication (>40% repeated is a failure)
        section_titles = [
            _text(s.get("title", "")).strip().lower()
            for s in site_sections
            if s.get("title")
        ]
        if section_titles:
            unique_count = len(set(section_titles))
            total_count = len(section_titles)
            unique_ratio = unique_count / total_count if total_count > 0 else 1.0

            if unique_ratio < 0.6:  # Less than 60% unique = quality fail
                logger.warning(
                    "Excessive section duplication detected (%s unique / %s total = %.1f%%). Returning quality score of 0.",
                    unique_count,
                    total_count,
                    unique_ratio * 100,
                )
                return 0
            elif unique_ratio < 0.8:  # 60-80% unique = warning, cap score
                logger.warning(
                    "Some section duplication detected (%s unique / %s total = %.1f%%). Capping quality score.",
                    unique_count,
                    total_count,
                    unique_ratio * 100,
                )
                # Will cap the final score at 70 later
                if screenshot_qa_score is not None:
                    screenshot_qa_score = min(screenshot_qa_score, 70)

    # Sanity-check unusually high screenshot QA scores
    if screenshot_qa_score is not None and screenshot_qa_score >= 80:
        if site_sections and sum(1 for s in site_sections if s.get("componentId")) == 0:
            logger.warning(
                "Screenshot QA gave %s but no sections have componentId. Reducing visual score to 20.",
                screenshot_qa_score,
            )
            screenshot_qa_score = 20

    # If screenshot QA provided a visual quality score, use it as the primary score
    if screenshot_qa_score is not None:
        score = screenshot_qa_score

        # Penalize missing requirements more heavily
        score -= min(len(missing_requirements), 5) * 3

        # Small bonuses for data completeness
        if brief.approvalState == "approved":
            score += 2
        if extraction.sourceCitations:
            score += 1
        if extraction.brandAssetCues:
            score += 1
        if site_sections:
            score += 1

        # Cap score if we lack strong source grounding
        if not extraction.sourceCitations or not extraction.brandAssetCues:
            score = min(score, 85)

        return max(0, min(100, score))

    # Fallback: very conservative data completeness score (no visual validation)
    score = 20
    if brief.approvalState == "approved":
        score += 5
    score += min(len(extraction.sourceCitations), 3) * 2
    score += min(len(extraction.brandAssetCues), 2) * 2
    score += min(len(site_sections), 3) * 2
    score += (
        4
        if brand_tokens["primaryColor"]["evidence"]["sourceKind"] == "source_backed"
        else 0
    )
    score += (
        3
        if brand_tokens["typography"]["evidence"]["sourceKind"] == "source_backed"
        else 0
    )
    score += int(diversity_score * 0.05)
    score -= min(len(missing_requirements), 5) * 5
    return max(0, min(100, score))


def _readiness_status(
    brief: SiteBrief, quality_score: int, missing_requirements: list[str]
) -> tuple[SiteReadinessStatus, SiteQaStatus]:
    if brief.approvalState != "approved":
        return "blocked", "fail"
    settings = get_settings()
    threshold = int(settings.visual_redesign_quality_threshold or 90)
    if quality_score >= threshold and not missing_requirements:
        return "ready_to_publish", "pass"
    review_floor = max(70, threshold - 15)
    if quality_score >= review_floor and len(missing_requirements) <= 2:
        return "ready_for_review", "warn"
    if quality_score >= 55:
        return "needs_review", "warn"
    return "blocked", "fail"


def _comparison_entries(
    *,
    brief: SiteBrief,
    theme: dict[str, Any],
    palette_mode: PaletteMode,
    hero: dict[str, Any],
    sections: list[dict[str, Any]],
    cta_strategy: dict[str, Any],
    brand_tokens: dict[str, Any],
) -> list[dict[str, Any]]:
    source_sections = (
        ", ".join(section.title for section in brief.recommendedSections[:4])
        or "No section titles were approved"
    )
    generated_sections = ", ".join(section["title"] for section in sections[:4])
    entries = [
        {
            "label": "Hero direction",
            "sourceValue": brief.recommendedHero.value
            or "No hero direction was approved",
            "generatedValue": hero["headline"],
            "status": "matched"
            if _text(brief.recommendedHero.value)
            and _text(brief.recommendedHero.value) in hero["headline"]
            else "inferred",
            "reason": "Hero copy is derived from the approved brief and the extracted positioning cues.",
            "evidence": hero["evidence"],
        },
        {
            "label": "Conversion angle",
            "sourceValue": brief.conversionAngle.value
            or "No conversion angle was approved",
            "generatedValue": cta_strategy["primary"]["label"],
            "status": "matched" if _text(brief.conversionAngle.value) else "inferred",
            "reason": "The CTA strategy is a source-safe translation of the approved conversion angle.",
            "evidence": cta_strategy["primary"]["evidence"],
        },
        {
            "label": "Theme selection",
            "sourceValue": brief.toneProfile.value or "Tone was not explicit",
            "generatedValue": theme["name"],
            "status": "inferred",
            "reason": theme["description"],
            "evidence": brand_tokens["visualTone"]["evidence"],
        },
        {
            "label": "Palette mode",
            "sourceValue": "Approved source citations and brand cues",
            "generatedValue": palette_mode,
            "status": "inferred",
            "reason": "Palette mode follows the extracted visual language and explicit source gaps.",
            "evidence": brand_tokens["backgroundColor"]["evidence"],
        },
        {
            "label": "Section stack",
            "sourceValue": source_sections,
            "generatedValue": generated_sections,
            "status": "inferred",
            "reason": "The section stack mirrors the approved section recommendations while staying source-safe.",
            "evidence": sections[0]["evidence"] if sections else None,
        },
    ]
    return entries


def _site_doc_to_current(doc: dict[str, Any]) -> GeneratedSite:
    return GeneratedSite.model_validate(doc)


def _site_version_doc_to_model(doc: dict[str, Any]) -> GeneratedSiteVersion:
    return GeneratedSiteVersion.model_validate(doc)


def _to_datetime(value: datetime | None) -> datetime:
    return _utc(value) or _now()


def _model_dump(value: Any) -> Any:
    return value.model_dump() if hasattr(value, "model_dump") else value


def _site_source_attribution(
    *,
    lead: Any | None,
    brief: Any | None,
    extraction: ExtractionSnapshot | None,
    theme: dict[str, Any],
    palette_mode: PaletteMode,
) -> dict[str, Any]:
    return {
        "leadId": getattr(lead, "id", ""),
        "sourceType": getattr(lead, "sourceType", None),
        "sourceRef": getattr(lead, "sourceRef", None),
        "companyName": getattr(lead, "companyName", None),
        "websiteUrl": getattr(lead, "websiteUrl", None),
        "normalizedDomain": getattr(lead, "normalizedDomain", None),
        "extractionId": getattr(extraction, "id", None),
        "extractionVersion": getattr(extraction, "version", None),
        "briefId": getattr(brief, "id", None),
        "briefVersion": getattr(brief, "version", None),
        "themeKey": theme["themeKey"],
        "paletteMode": palette_mode,
    }


def _check_theme_diversity_constraint(
    current_batch_sites: list[GeneratedSite],  # noqa: ARG001
    proposed_theme_key: str,  # noqa: ARG001
    proposed_palette_mode: PaletteMode,  # noqa: ARG001
) -> tuple[bool, str]:
    """Theme diversity constraint - always allows generation.

    Diversity tracking is for metrics only, not a hard gate.
    """
    return True, ""


def _compute_diversity_score(
    current_batch_sites: list[GeneratedSite],
    theme_key: str,
    palette_mode: PaletteMode,
) -> int:
    """
    Compute a diversity score (0-100) based on theme/palette uniqueness in the batch.

    Higher score = more unique combination in the current batch.
    """
    if not current_batch_sites:
        return 50

    theme_counts = Counter(site.themeKey for site in current_batch_sites)
    palette_counts = Counter(site.paletteMode for site in current_batch_sites)

    theme_count = theme_counts.get(theme_key, 0)
    palette_count = palette_counts.get(palette_mode, 0)

    batch_size = len(current_batch_sites)
    theme_rarity = 1 - (theme_count / batch_size) if batch_size > 0 else 0.5
    palette_rarity = 1 - (palette_count / batch_size) if batch_size > 0 else 0.5

    score = int((theme_rarity * 0.6 + palette_rarity * 0.4) * 100)
    return max(0, min(100, score))


def _diversity_notes(
    current: GeneratedSite | None,
    theme: dict[str, Any],
    palette_mode: PaletteMode,
    references: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []
    if current is not None:
        if current.themeKey == theme["themeKey"]:
            notes.append(
                "Theme matches the prior version; review for visual repetition before publish."
            )
        if current.paletteMode == palette_mode:
            notes.append(
                "Palette matches the prior version; confirm the choice is still source-backed and reviewed."
            )
    if not notes and references:
        notes.append(
            "Theme and palette are derived from the source cues and remain traceable to extracted evidence."
        )
    return notes


def _review_state_from(
    site: GeneratedSite | None, review: dict[str, Any] | None = None
) -> ReviewWorkflowState:
    if review:
        outcome = review.get("outcome")
        blocked_reason = _text(review.get("blockedReason"))
        if blocked_reason or outcome == "fail":
            return "blocked"
        if outcome == "warn":
            return "warned"
        if outcome == "pass":
            return "approved"
    if site is None:
        return "not_reviewed"
    if site.qaStatus == "fail" or site.readinessStatus == "blocked":
        return "blocked"
    if site.qaStatus == "warn":
        return "warned"
    if site.readinessStatus == "ready_to_publish":
        return "approved"
    if site.readinessStatus in {"ready_for_review", "needs_review"}:
        return "in_review"
    return "not_reviewed"


def _publish_approval_state(
    site: GeneratedSite | None,
    review_state: ReviewWorkflowState,
    missing_requirements: list[str],
) -> PublishApprovalState:
    if site is None:
        return "pending"
    if review_state == "blocked" or site.qaStatus == "fail" or missing_requirements:
        return "blocked"
    if site.readinessStatus == "ready_to_publish" and site.qaStatus == "pass":
        return "approved"
    return "pending"


def _review_checklist_pass(review_rubric: list[dict[str, Any]]) -> bool:
    return all(item.get("status") != "fail" for item in review_rubric)


def _screenshot_models(
    screenshots: list[dict[str, Any]],
) -> list[SiteScreenshotMetadata]:
    return [SiteScreenshotMetadata.model_validate(item) for item in screenshots]


def _queue_item_from_site(site: GeneratedSite) -> SiteReviewQueueItem:
    return SiteReviewQueueItem(
        siteId=site.id,
        leadId=site.leadId,
        version=site.version,
        previewSlug=site.previewSlug,
        previewUrl=site.previewUrl,
        themeKey=site.themeKey,
        paletteMode=site.paletteMode,
        qualityScore=site.qualityScore,
        readinessStatus=site.readinessStatus,
        qaStatus=site.qaStatus,
        publishApprovalState=site.publishApprovalState,
        reviewState=site.browserReviewState,
        missingRequirements=list(site.missingRequirements),
        reviewRubric=list(site.reviewRubric),
        screenshotCount=len(site.screenshotRefs),
        updatedAt=site.updatedAt,
    )


def _handoff_record_from_site(
    site: GeneratedSite, review: dict[str, Any] | None = None
) -> SiteHandoffRecord:
    return SiteHandoffRecord(
        id=site.handoffRecordId or site.id,
        siteId=site.id,
        leadId=site.leadId,
        version=site.version,
        status="ready"
        if site.publishApprovalState == "approved"
        and site.qaStatus == "pass"
        and not site.missingRequirements
        else "blocked",
        sourceAttribution=SiteSourceAttribution.model_validate(site.sourceAttribution)
        if site.sourceAttribution
        else SiteSourceAttribution(leadId=site.leadId),
        previewSlug=site.previewSlug,
        previewUrl=site.previewUrl,
        themeKey=site.themeKey,
        paletteMode=site.paletteMode,
        qualityScore=site.qualityScore,
        readinessStatus=site.readinessStatus,
        qaStatus=site.qaStatus,
        publishApprovalState=site.publishApprovalState,
        reviewRecordId=review.get("id") if review else site.latestReviewId,
        reviewOutcome=review.get("outcome") if review else None,
        reviewChecklist=[
            SiteReviewChecklistItem.model_validate(item)
            for item in (review.get("checklist", []) if review else [])
        ],
        screenshots=_screenshot_models(review.get("screenshots", []))
        if review
        else list(site.screenshotRefs),
        sourceTraceability=list(site.sourceTraceability),
        missingRequirements=list(site.missingRequirements),
        exportMetadata=site.exportMetadata,
        createdAt=site.createdAt,
        updatedAt=site.updatedAt,
    )


class SiteRepository:
    def __init__(self) -> None:
        self._memory_lock = asyncio.Lock()
        self._sites: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[dict[str, Any]]] = {}
        self._overrides: dict[str, list[dict[str, Any]]] = {}
        self._exports: dict[str, list[dict[str, Any]]] = {}
        self._reviews: dict[str, dict[str, Any]] = {}
        self._handoffs: dict[str, dict[str, Any]] = {}
        self._memory_ready = False
        self._screenshot_comparator = ScreenshotComparator()

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None or self._memory_ready:
            return
        self._memory_ready = True
        await database["generated_sites"].create_index("id", unique=True)
        await database["generated_sites"].create_index("leadId")
        await database["generated_sites"].create_index("previewSlug")
        await database["generated_site_versions"].create_index("siteId")
        await database["generated_site_versions"].create_index(
            [("siteId", 1), ("version", -1)]
        )
        await database["site_overrides"].create_index("siteId")
        await database["site_overrides"].create_index(
            [("siteId", 1), ("createdAt", -1)]
        )
        await database["site_overrides"].create_index([("siteId", 1), ("path", 1)])
        await database["site_exports"].create_index("siteId")
        await database["site_exports"].create_index([("siteId", 1), ("createdAt", -1)])
        await database["site_reviews"].create_index("siteId")
        await database["site_reviews"].create_index([("siteId", 1), ("reviewedAt", -1)])
        await database["site_handoffs"].create_index("siteId")
        await database["site_handoffs"].create_index([("siteId", 1), ("createdAt", -1)])

    def get_theme_library(self) -> ThemeLibraryResponse:
        return ThemeLibraryResponse(
            items=[ThemeVariant.model_validate(theme) for theme in THEME_LIBRARY]
        )

    async def get_diversity_report(self, limit: int = 100) -> dict[str, Any]:
        """
        Returns batch-level diversity metrics for the last N sites.
        """
        sites = await self._list_sites(limit=limit, offset=0)

        # Compute theme distribution
        theme_counts = Counter(site.themeKey for site in sites)
        theme_distribution = {
            k: {
                "count": v,
                "percentage": round((v / len(sites)) * 100, 1) if sites else 0,
            }
            for k, v in theme_counts.items()
        }

        # Compute palette distribution
        palette_counts = Counter(site.paletteMode for site in sites)
        palette_distribution = {
            k: {
                "count": v,
                "percentage": round((v / len(sites)) * 100, 1) if sites else 0,
            }
            for k, v in palette_counts.items()
        }

        # Compute motion distribution
        motion_counts: dict[str, int] = {}
        for site in sites:
            theme = _theme_data(site.themeKey)
            motion_preset = theme.get("motionPreset", "unknown")
            motion_counts[motion_preset] = motion_counts.get(motion_preset, 0) + 1
        motion_distribution = {
            k: {
                "count": v,
                "percentage": round((v / len(sites)) * 100, 1) if sites else 0,
            }
            for k, v in motion_counts.items()
        }

        # Compute spacing distribution
        spacing_counts: dict[str, int] = {}
        for site in sites:
            theme = _theme_data(site.themeKey)
            spacing_style = theme.get("spacingStyle", "unknown")
            spacing_counts[spacing_style] = spacing_counts.get(spacing_style, 0) + 1
        spacing_distribution = {
            k: {
                "count": v,
                "percentage": round((v / len(sites)) * 100, 1) if sites else 0,
            }
            for k, v in spacing_counts.items()
        }

        # Detect duplicates (identical theme+palette combinations)
        combinations = [(site.themeKey, site.paletteMode) for site in sites]
        combo_counts = Counter(combinations)
        duplicate_count = sum(1 for count in combo_counts.values() if count > 1)

        return {
            "themeDistribution": theme_distribution,
            "paletteDistribution": palette_distribution,
            "motionDistribution": motion_distribution,
            "spacingDistribution": spacing_distribution,
            "duplicateCount": duplicate_count,
            "totalSites": len(sites),
        }

    async def _maybe_queue_auto_iteration(
        self,
        *,
        site_id: str,
        job_id: str,
        request: SiteGenerateRequest | None,
    ) -> None:
        """Best-effort scheduling of an automatic refinement run.

        After a generation job completes and screenshot QA has run, this helper
        inspects the latest site and job metadata. When the visual QA score is
        below the configured threshold, an improvement brief was generated, and
        the site is still within the visual_redesign_max_iterations budget, it
        queues a follow-up generation job that will apply the automatic
        refinement hints before building the next section stack.

        This function is intentionally defensive: any errors are logged and
        swallowed so that the primary generation job result is never marked as
        failed just because auto-iteration scheduling had an issue.
        """

        settings = get_settings()
        if not settings.visual_redesign_enabled:
            return

        # Treat values <= 1 as "no automatic iteration".
        try:
            max_iterations = int(getattr(settings, "visual_redesign_max_iterations", 0))
        except Exception:
            max_iterations = 0
        if max_iterations <= 1:
            return

        try:
            # Load the latest generated site to inspect version and any
            # improvement recommendations produced during screenshot QA.
            site = await self.get_site(site_id)
            if site is None:
                return

            try:
                job_doc = await lead_repository.get_job_doc(job_id)
            except Exception:
                job_doc = None

            metadata = (job_doc or {}).get("metadata", {}) or {}
            screenshot_qa = metadata.get("screenshotQA") or {}
            screenshot_quality = screenshot_qa.get("qualityScore")
            screenshot_success = screenshot_qa.get("success", False)

            if not screenshot_success or screenshot_quality is None:
                return

            threshold = int(getattr(settings, "visual_redesign_quality_threshold", 95))
            if int(screenshot_quality) >= threshold:
                return

            # Enforce a hard cap on how many generations we will run
            # automatically. Version numbers are 1-based, so with
            # max_iterations=2 we allow a single follow-up pass.
            current_version = int(getattr(site, "version", 0))
            if current_version >= max_iterations:
                return

            if not getattr(site, "improvementRecommendations", None):
                return

            logger.info(
                "Queuing automatic refinement generation for %s (version %s -> %s)",
                site_id,
                current_version,
                current_version + 1,
            )

            force_flag = bool(getattr(request, "force", False)) if request else False
            auto_request = SiteGenerateRequest(
                force=force_flag, refinementPromptId=None
            )

            await self.queue_generation_job(site_id, request=auto_request)
        except Exception as exc:  # pragma: no cover - defensive path
            logging.getLogger(__name__).error(
                "Failed to queue automatic refinement generation for %s: %s",
                site_id,
                exc,
                exc_info=True,
            )

    async def submit_refinement_prompt(
        self,
        site_id: str,
        prompt_text: str,
        operator_id: str,
    ) -> str | None:
        """Store operator refinement prompt and return its ID without triggering regeneration."""

        await self._maybe_ensure_indexes()
        prompt_id = uuid4().hex
        now = _now()

        record = RefinementPromptRecord(
            id=prompt_id,
            submittedAt=now,
            operatorId=operator_id,
            promptText=prompt_text,
            resultVersionId=None,
            status="pending",
            qualityScore=None,
            failureReason=None,
            notes=None,
        ).model_dump()

        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc is None:
                    return None
                history = list(doc.get("promptHistory") or [])
                history.append(record)
                doc["promptHistory"] = history
                doc["refinementPromptId"] = prompt_id
                doc["updatedAt"] = now
            return prompt_id

        result = await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {"refinementPromptId": prompt_id, "updatedAt": now},
                "$push": {"promptHistory": record},
            },
        )
        if result.matched_count == 0:
            return None
        return prompt_id

    async def update_prompt_result(
        self,
        site_id: str,
        prompt_id: str,
        version_id: str,
        quality_score: int,
        status: str,
        failure_reason: str | None = None,
    ) -> None:
        """Update a stored refinement prompt record with the outcome of regeneration."""

        await self._maybe_ensure_indexes()
        now = _now()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if not doc:
                    return
                history = list(doc.get("promptHistory") or [])
                for item in history:
                    if item.get("id") == prompt_id:
                        item["resultVersionId"] = version_id
                        item["qualityScore"] = int(quality_score)
                        item["status"] = status
                        item["failureReason"] = failure_reason
                        break
                doc["promptHistory"] = history
                doc["updatedAt"] = now
            return

        doc = await database["generated_sites"].find_one({"id": site_id})
        if not doc:
            return
        history = list(doc.get("promptHistory") or [])
        for item in history:
            if item.get("id") == prompt_id:
                item["resultVersionId"] = version_id
                item["qualityScore"] = int(quality_score)
                item["status"] = status
                item["failureReason"] = failure_reason
                break
        doc["promptHistory"] = history
        doc["updatedAt"] = now
        await database["generated_sites"].replace_one({"id": site_id}, doc, upsert=True)

    async def get_prompt_history(self, site_id: str) -> list[RefinementPromptRecord]:
        """Return refinement prompt history for a site."""

        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                history = list(doc.get("promptHistory") or []) if doc else []
        else:
            doc = await database["generated_sites"].find_one({"id": site_id})
            history = list(doc.get("promptHistory") or []) if doc else []

        return [RefinementPromptRecord.model_validate(item) for item in history]

    async def get_site(self, site_id: str) -> GeneratedSite | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc:
                    site = _site_doc_to_current(doc)
                    # Populate override diffs
                    diffs = self.get_override_diff(site_id)
                    site.overrideDiffs = diffs
                    return site
                return None
        doc = await database["generated_sites"].find_one({"id": site_id})
        if doc:
            site = _site_doc_to_current(doc)
            # Populate override diffs
            diffs = self.get_override_diff(site_id)
            site.overrideDiffs = diffs
            return site
        return None

    async def get_site_by_slug(self, slug: str) -> GeneratedSite | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                for doc in self._sites.values():
                    if doc.get("previewSlug") == slug or doc.get("id") == slug:
                        return _site_doc_to_current(doc)
                return None
        doc = await database["generated_sites"].find_one({"previewSlug": slug})
        if doc is None:
            doc = await database["generated_sites"].find_one({"id": slug})
        return _site_doc_to_current(doc) if doc else None

    async def list_versions(self, site_id: str) -> GeneratedSiteVersionResponse | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = list(self._versions.get(site_id, []))
                docs.sort(key=lambda item: item.get("version", 0), reverse=True)
                return GeneratedSiteVersionResponse(
                    siteId=site_id,
                    previewSlug=site.previewSlug,
                    previewUrl=site.previewUrl,
                    currentVersion=site.version,
                    items=[_site_version_doc_to_model(doc) for doc in docs],
                    updatedAt=site.updatedAt,
                )
        cursor = (
            database["generated_site_versions"]
            .find({"siteId": site_id})
            .sort("version", -1)
        )
        docs = await cursor.to_list(length=50)
        return GeneratedSiteVersionResponse(
            siteId=site_id,
            previewSlug=site.previewSlug,
            previewUrl=site.previewUrl,
            currentVersion=site.version,
            items=[_site_version_doc_to_model(doc) for doc in docs],
            updatedAt=site.updatedAt,
        )

    async def get_compare(self, site_id: str) -> SiteCompareResponse | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        return SiteCompareResponse(
            siteId=site.id,
            leadId=site.leadId,
            briefId=site.briefId,
            briefVersion=site.briefVersion,
            version=site.version,
            previewSlug=site.previewSlug,
            previewUrl=site.previewUrl,
            qualityScore=site.qualityScore,
            readinessStatus=site.readinessStatus,
            qaStatus=site.qaStatus,
            entries=site.comparisonEntries,
            reviewRubric=site.reviewRubric,
            missingRequirements=site.missingRequirements,
            updatedAt=site.updatedAt,
        )

    async def list_review_queue(
        self, *, limit: int = 25, offset: int = 0
    ) -> SiteReviewQueueResponse:
        await self._maybe_ensure_indexes()
        sites = await self._list_sites(limit=limit, offset=offset)
        items = [_queue_item_from_site(site) for site in sites]
        total = await self._count_sites()

        theme_counts = Counter(item.themeKey for item in items)
        palette_counts = Counter(item.paletteMode for item in items)

        # Compute motion diversity
        motion_diversity: dict[str, int] = {}
        for theme_key, count in theme_counts.items():
            theme = _theme_data(theme_key)
            motion_preset = theme.get("motionPreset", "unknown")
            motion_diversity[motion_preset] = (
                motion_diversity.get(motion_preset, 0) + count
            )

        # Compute spacing diversity
        spacing_diversity: dict[str, int] = {}
        for theme_key, count in theme_counts.items():
            theme = _theme_data(theme_key)
            spacing_style = theme.get("spacingStyle", "unknown")
            spacing_diversity[spacing_style] = (
                spacing_diversity.get(spacing_style, 0) + count
            )

        automation_summary = {
            "ready": sum(
                1
                for item in items
                if item.publishApprovalState == "approved"
                and not item.missingRequirements
                and item.qaStatus == "pass"
            ),
            "needsReview": sum(
                1 for item in items if item.reviewState in {"in_review", "not_reviewed"}
            ),
            "blocked": sum(
                1
                for item in items
                if item.publishApprovalState == "blocked"
                or item.qaStatus == "fail"
                or bool(item.missingRequirements)
            ),
            "regenerationBacklog": sum(1 for item in items if item.qaStatus == "fail"),
        }
        handoff_ready_sites = [
            item.siteId
            for item in items
            if item.publishApprovalState == "approved"
            and not item.missingRequirements
            and item.qaStatus == "pass"
        ]

        return SiteReviewQueueResponse(
            items=items,
            pagination={"total": total, "limit": limit, "offset": offset},
            themeDiversity=dict(theme_counts),
            paletteDiversity=dict(palette_counts),
            motionDiversity=motion_diversity,
            spacingDiversity=spacing_diversity,
            automationSummary=automation_summary,
            handoffReadySiteIds=handoff_ready_sites,
        )

    async def get_review(self, site_id: str) -> SiteReviewRecord | None:
        await self._maybe_ensure_indexes()
        review_doc = await self._get_review_doc(site_id)
        if review_doc is None:
            return None
        return SiteReviewRecord.model_validate(review_doc)

    async def upsert_review(
        self,
        site_id: str,
        request: SiteReviewRequest | SiteReviewPatchRequest,
        *,
        actor: str | None = None,
    ) -> SiteReviewRecord | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        existing = await self._get_review_doc(site_id)
        now = _now()
        checklist = list(
            getattr(request, "checklist", None)
            or (existing.get("checklist", []) if existing else [])
        )
        screenshots = list(
            getattr(request, "screenshots", None)
            or (existing.get("screenshots", []) if existing else [])
        )
        outcome = getattr(request, "outcome", None) or (
            existing.get("outcome") if existing else site.qaStatus
        )
        blocked_reason = (
            getattr(request, "blockedReason", None)
            if getattr(request, "blockedReason", None) is not None
            else (existing.get("blockedReason") if existing else None)
        )
        notes = (
            getattr(request, "notes", None)
            if getattr(request, "notes", None) is not None
            else (existing.get("notes") if existing else None)
        )
        browser_preview_url = (
            getattr(request, "browserPreviewUrl", None)
            if hasattr(request, "browserPreviewUrl")
            else (existing.get("browserPreviewUrl") if existing else None)
        )
        review_state = _review_state_from(
            site, {"outcome": outcome, "blockedReason": blocked_reason}
        )
        # Prefer master brief for attribution, fall back to legacy brief
        master_brief = await lead_repository.get_master_brief(site_id)
        legacy_brief = await lead_repository.get_brief(site_id)
        brief_for_attribution = master_brief or legacy_brief

        source_attribution = _site_source_attribution(
            lead=await lead_repository.get_lead(site_id),
            brief=brief_for_attribution,
            extraction=await lead_repository.get_extraction(site_id),
            theme={"themeKey": site.themeKey},
            palette_mode=site.paletteMode,
        )
        record = {
            "id": existing.get("id") if existing else uuid4().hex,
            "siteId": site_id,
            "leadId": site.leadId,
            "version": site.version,
            "browserPreviewUrl": browser_preview_url,
            "outcome": outcome,
            "reviewState": review_state,
            "checklist": [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in checklist
            ],
            "screenshots": [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in screenshots
            ],
            "notes": notes,
            "blockedReason": blocked_reason,
            "sourceAttribution": source_attribution,
            "createdBy": existing.get("createdBy") if existing else actor,
            "reviewedAt": existing.get("reviewedAt") if existing else now,
            "updatedAt": now,
        }
        record["reviewedAt"] = now
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._reviews[site_id] = record
                await self._apply_review_to_site(site_id, record)
                return SiteReviewRecord.model_validate(record)
        await database["site_reviews"].replace_one(
            {"siteId": site_id}, record, upsert=True
        )
        await self._apply_review_to_site(site_id, record)
        return SiteReviewRecord.model_validate(record)

    async def get_handoff(self, site_id: str) -> SiteHandoffRecord | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        review = await self._get_review_doc(site_id)
        record = self._handoff_doc_for_site(site, review)
        return SiteHandoffRecord.model_validate(record)

    async def publish_handoff(self, site_id: str) -> SiteHandoffRecord | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        review = await self._get_review_doc(site_id)
        record = self._handoff_doc_for_site(site, review)
        now = _now()
        record["updatedAt"] = now
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._handoffs[site_id] = record
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["handoffRecordId"] = record["id"]
                    doc["publishApprovalState"] = record["publishApprovalState"]
                    doc["browserReviewState"] = (
                        record["reviewRecordId"]
                        and _review_state_from(site, review)
                        or doc.get("browserReviewState", "not_reviewed")
                    )
                    doc["updatedAt"] = now
                return SiteHandoffRecord.model_validate(record)
        await database["site_handoffs"].replace_one(
            {"siteId": site_id}, record, upsert=True
        )
        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "handoffRecordId": record["id"],
                    "publishApprovalState": record["publishApprovalState"],
                    "updatedAt": now,
                }
            },
        )
        return SiteHandoffRecord.model_validate(record)

    async def retry_generation(self, site_id: str) -> JobSummary | None:
        site = await self.get_site(site_id)
        if site is None:
            return None
        return await self.queue_generation_job(site_id)

    async def create_override(
        self,
        site_id: str,
        request: SiteOverrideCreateRequest,
        *,
        actor: str | None = None,
    ) -> SiteOverrideRecord | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        now = _now()
        record = SiteOverrideRecord(
            id=uuid4().hex,
            siteId=site.id,
            leadId=site.leadId,
            version=site.version,
            scope=request.scope,
            path=request.path.strip(),
            value=request.value.strip(),
            previousValue=request.previousValue.strip()
            if request.previousValue
            else None,
            reason=request.reason.strip() if request.reason else None,
            sourceType=request.sourceType,
            status="active",
            createdBy=actor,
            createdAt=now,
            updatedAt=now,
        )
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._overrides.setdefault(site_id, []).append(record.model_dump())
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["overrides"] = list(self._overrides.get(site_id, []))
                    doc["overrideCount"] = len(doc["overrides"])
                    doc["updatedAt"] = now
                await analytics_repository.record_admin_event(
                    event_type="site_override_applied",
                    event_name=f"Override stored for {record.path}",
                    site_id=site.id,
                    lead_id=site.leadId,
                    metadata={"scope": record.scope, "path": record.path},
                )
                return record
        await database["site_overrides"].insert_one(record.model_dump())
        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {"overrideCount": site.overrideCount + 1, "updatedAt": now},
                "$push": {"overrides": record.model_dump()},
            },
        )
        await analytics_repository.record_admin_event(
            event_type="site_override_applied",
            event_name=f"Override stored for {record.path}",
            site_id=site.id,
            lead_id=site.leadId,
            metadata={"scope": record.scope, "path": record.path},
        )
        return record

    def get_override_diff(self, site_id: str) -> list[dict[str, Any]]:
        """
        Returns computed diffs for all active overrides on a site.

        For each override, includes:
        - override record (path, scope, value, previousValue, reason)
        - current value in the generated site
        - computed diff showing what changed

        Returns a list of diff dictionaries.
        """
        site = self._sites.get(site_id)
        if not site:
            return []

        diffs: list[dict[str, Any]] = []
        overrides = site.get("overrides", [])

        for override in overrides:
            if override.get("status") != "active":
                continue

            previous_value = override.get("previousValue")
            current_value = override.get("value")
            path = override.get("path", "")

            # Get the current value from the generated site by traversing the path
            site_current_value = self._get_nested_value(site, path)

            # Determine diff type
            diff_type = "changed"
            if previous_value is None:
                diff_type = "added"
            elif current_value is None or current_value == "":
                diff_type = "removed"

            diffs.append(
                {
                    "overrideId": override.get("id"),
                    "path": path,
                    "scope": override.get("scope"),
                    "previousValue": previous_value,
                    "currentValue": current_value,
                    "siteCurrentValue": site_current_value,
                    "diffType": diff_type,
                }
            )

        return diffs

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """
        Helper to get a nested value from a dict using dot notation path.
        """
        keys = path.split(".")
        current = obj
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    async def queue_generation_job(
        self, site_id: str, request: SiteGenerateRequest | None = None
    ) -> JobSummary | None:
        await self._maybe_ensure_indexes()
        lead = await lead_repository.get_lead(site_id)
        if lead is None:
            return None

        # Check for master brief first (AI-native generation), fall back to legacy brief
        master_brief = await lead_repository.get_master_brief(site_id)
        brief = await lead_repository.get_brief(site_id)

        # Allow generation if EITHER master brief OR legacy brief is approved
        has_approved_brief = (
            master_brief is not None and master_brief.approvalState == "approved"
        ) or (brief is not None and brief.approvalState == "approved")
        if not has_approved_brief:
            raise ValueError("brief_not_approved")

        extraction = await lead_repository.get_extraction(site_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("extraction_required")

        current = await self.get_site(site_id)
        refinement_prompt_id = (
            getattr(request, "refinementPromptId", None) if request else None
        )

        # If this generation was triggered by an operator refinement prompt, call Gemini
        # to refine the existing visual redesign brief before building the section stack.
        if refinement_prompt_id:
            try:
                # Find the stored prompt text
                database = get_database()
                prompt_text: str | None = None
                if database is None:
                    async with self._memory_lock:
                        doc = self._sites.get(site_id)
                        if doc:
                            for item in doc.get("promptHistory", []) or []:
                                if item.get("id") == refinement_prompt_id:
                                    prompt_text = _text(item.get("promptText"))
                                    break
                else:
                    doc = await database["generated_sites"].find_one({"id": site_id})
                    if doc:
                        for item in doc.get("promptHistory", []) or []:
                            if item.get("id") == refinement_prompt_id:
                                prompt_text = _text(item.get("promptText"))
                                break

                if prompt_text and brief:
                    extraction_summary = _text(extraction.summary.positioningSummary)
                    brief_summary = _text(brief.companySummary.value)
                    brand_tokens_summary = ""
                    if current and getattr(current, "brandTokens", None):
                        try:
                            brand_tokens_summary = json.dumps(
                                current.brandTokens.model_dump(), default=str
                            )
                        except Exception:
                            brand_tokens_summary = ""

                    llm = get_llm_client()
                    refinement = await llm.refine_brief_with_operator_prompt(
                        extraction_summary=extraction_summary,
                        current_brief_summary=brief_summary,
                        brand_tokens_summary=brand_tokens_summary,
                        operator_prompt=prompt_text,
                    )

                    updated_visual = _apply_refinement_to_visual_redesign(
                        brief=brief, refinement=refinement
                    )
                    if updated_visual:
                        await lead_repository.update_brief_visual_redesign(
                            lead_id=site_id,
                            visual_redesign_briefs=updated_visual,
                        )
                        # Refresh brief snapshot so section stack sees the refined redesign
                        brief = await lead_repository.get_brief(site_id) or brief
            except Exception as exc:  # pragma: no cover - defensive logging path
                logging.getLogger(__name__).error(
                    "Failed to apply refinement prompt %s for site %s: %s",
                    refinement_prompt_id,
                    site_id,
                    exc,
                )
        else:
            # Automatic refinement path: if the previous generated site has
            # improvement recommendations from screenshot QA and we are
            # still within the visual redesign iteration budget, convert
            # those into refinement hints for the visual redesign brief.
            settings = get_settings()
            if (
                settings.visual_redesign_enabled
                and current is not None
                and getattr(current, "improvementRecommendations", None)
                and int(getattr(current, "version", 0))
                < int(settings.visual_redesign_max_iterations)
            ):
                try:
                    auto_refinement = _auto_refinement_from_improvement_brief(
                        current.improvementRecommendations  # type: ignore[arg-type]
                    )
                    if (
                        auto_refinement.get("componentSuggestions")
                        and brief is not None
                    ):
                        updated_visual = _apply_refinement_to_visual_redesign(
                            brief=brief, refinement=auto_refinement
                        )
                        if updated_visual:
                            await lead_repository.update_brief_visual_redesign(
                                lead_id=site_id,
                                visual_redesign_briefs=updated_visual,
                            )
                            brief = await lead_repository.get_brief(site_id) or brief
                except Exception as exc:  # pragma: no cover - defensive logging path
                    logging.getLogger(__name__).error(
                        "Failed to apply automatic improvement refinement for site %s: %s",
                        site_id,
                        exc,
                    )
        next_version = int(current.version if current else 0) + 1
        job_type = "site_generate" if current is None else "site_republish"

        # Check diversity constraints before generation (only for legacy brief path)
        # Master brief path skips diversity checks as AI generation handles variety naturally
        if brief and (not request or not request.force):
            batch_sites = [
                site
                for site in await self._list_sites(limit=50, offset=0)
                if site.id != site_id
            ]
            # Compute proposed theme and palette from signals
            signals = " ".join(
                [
                    _text(lead.companyName),
                    _text(lead.industry),
                    _text(brief.companySummary.value),
                    _text(brief.audienceHypothesis.value),
                    _text(brief.toneProfile.value),
                    _text(brief.conversionAngle.value),
                    _text(extraction.summary.positioningSummary),
                    " ".join(extraction.summary.toneClues),
                    " ".join(cue.label for cue in extraction.brandAssetCues),
                    " ".join(cue.value for cue in extraction.brandAssetCues),
                ]
            )
            proposed_theme, _ = _theme_for_signals(signals, extraction)
            proposed_palette, _ = _palette_mode_from_signals(
                " ".join(
                    [
                        _text(brief.toneProfile.value),
                        _text(extraction.summary.positioningSummary),
                        " ".join(extraction.summary.toneClues),
                        " ".join(
                            cue.label
                            for cue in extraction.brandAssetCues
                            if cue.assetType == "color"
                        ),
                        " ".join(
                            cue.value
                            for cue in extraction.brandAssetCues
                            if cue.assetType == "color"
                        ),
                    ]
                ),
                extraction,
            )

            # Check for operator theme override
            overrides = await self._site_overrides(site_id)
            for ov in overrides:
                path = _text(ov.get("path"))
                val = _text(ov.get("value"))
                if path in ("themeKey", "theme.key") and val:
                    proposed_theme = _theme_data(val)
                    break

            allowed, reason = _check_theme_diversity_constraint(
                batch_sites,
                proposed_theme["themeKey"],
                proposed_palette,
            )
            if not allowed:
                raise ValueError(f"diversity_constraint: {reason}")

        job = await lead_repository.create_job(
            lead_ids=[site_id],
            job_type=job_type,
            status="queued",
            progress=0,
            step="Queued for generation",
            metadata={
                "siteId": site_id,
                "leadId": site_id,
                "briefId": brief.id
                if brief
                else (master_brief.id if master_brief else ""),
                "briefVersion": brief.version
                if brief
                else (master_brief.version if master_brief else 0),
                "nextVersion": next_version,
                "request": request.model_dump() if request else {},
            },
        )
        await self._dispatch_generation_job(
            site_id=site_id, job_id=job.id, request=request
        )
        return job

    async def generate_site(
        self, site_id: str, request: SiteGenerateRequest | None = None
    ) -> GeneratedSite | None:
        job = await self.queue_generation_job(site_id, request=request)
        if job is None:
            return None
        return await self.get_site(site_id)

    async def run_generation_job(
        self, *, site_id: str, job_id: str, request: SiteGenerateRequest | None = None
    ) -> GeneratedSite | None:
        from typing import cast
        from ..schemas.site import PaletteMode

        await self._maybe_ensure_indexes()
        settings = get_settings()
        lead = await lead_repository.get_lead(site_id)
        if lead is None:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Lead missing for generation",
                error_message="Lead not found",
                finished=True,
                lead_ids=[site_id],
            )
            return None

        # Check for master brief (AI generation support)
        master_brief = await lead_repository.get_master_brief(site_id)
        use_ai_generation = (
            master_brief is not None and master_brief.approvalState == "approved"
        )

        brief = await lead_repository.get_brief(site_id)
        # Allow generation if EITHER master brief OR legacy brief is approved
        has_approved_brief = use_ai_generation or (
            brief is not None and brief.approvalState == "approved"
        )
        if not has_approved_brief:
            raise ValueError("brief_not_approved")
        extraction = await lead_repository.get_extraction(site_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("extraction_required")

        # High-level generation trace
        logger.info("=== Starting site generation for %s ===", site_id)
        if use_ai_generation:
            logger.info(
                "AI generation mode: Master brief %s approved",
                master_brief.id if master_brief else "unknown",
            )
        if brief:
            logger.info(
                "Legacy Brief %s v%s with %d recommended sections",
                brief.id,
                brief.version,
                len(getattr(brief, "recommendedSections", []) or []),
            )
        logger.info(
            "Extraction: %d citations, %d brand cues, %d extracted sections",
            len(extraction.sourceCitations),
            len(extraction.brandAssetCues),
            len(getattr(extraction, "sectionInventory", []) or []),
        )

        current = await self.get_site(site_id)
        refinement_prompt_id = (
            getattr(request, "refinementPromptId", None) if request else None
        )
        next_version = int(current.version if current else 0) + 1
        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            status="running",
            progress=15,
            step="Selecting theme and palette",
            lead_ids=[site_id],
            metadata={
                "siteId": site_id,
                "leadId": site_id,
                "briefId": brief.id
                if brief
                else (master_brief.id if master_brief else ""),
                "briefVersion": brief.version
                if brief
                else (master_brief.version if master_brief else 0),
                "nextVersion": next_version,
            },
        )

        # If we only have master_brief (no legacy brief), use AI-native generation
        if brief is None and use_ai_generation and master_brief is not None:
            from app.core.ai_site_generation import generate_landing_page_code

            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                progress=40,
                step="Generating landing page code from master brief",
            )

            result = await generate_landing_page_code(
                master_brief=master_brief,
                extraction=extraction,
                site_id=site_id,
            )

            if not result.get("success"):
                await lead_repository._update_job(  # noqa: SLF001
                    job_id,
                    status="failed",
                    progress=100,
                    step="Code generation failed",
                    error_message=result.get("error", "Unknown error"),
                    finished=True,
                    lead_ids=[site_id],
                )
                return None

            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                progress=100,
                step="Generation complete",
                status="completed",
                finished=True,
                lead_ids=[site_id],
            )
            return await self.get_site(site_id)

        # Legacy brief path - brief is guaranteed non-None here
        assert brief is not None

        await lead_repository._update_job(
            job_id, progress=35, step="Building source-safe brand tokens"
        )  # noqa: SLF001

        theme, theme_rationale = _theme_for_signals(
            " ".join(
                [
                    _text(lead.companyName),
                    _text(lead.industry),
                    _text(brief.companySummary.value),
                    _text(brief.audienceHypothesis.value),
                    _text(brief.toneProfile.value),
                    _text(brief.conversionAngle.value),
                    _text(extraction.summary.positioningSummary),
                    " ".join(extraction.summary.toneClues),
                    " ".join(cue.label for cue in extraction.brandAssetCues),
                    " ".join(cue.value for cue in extraction.brandAssetCues),
                ]
            ),
            extraction,
        )
        palette_mode, palette_rationale = _palette_mode_from_signals(
            " ".join(
                [
                    _text(brief.toneProfile.value),
                    _text(extraction.summary.positioningSummary),
                    " ".join(extraction.summary.toneClues),
                    " ".join(
                        cue.label
                        for cue in extraction.brandAssetCues
                        if cue.assetType == "color"
                    ),
                    " ".join(
                        cue.value
                        for cue in extraction.brandAssetCues
                        if cue.assetType == "color"
                    ),
                ]
            ),
            extraction,
        )
        refs = _site_refs(brief, extraction)

        # Detect industry for enhanced color system and design customization
        services_list = [
            s.title for s in getattr(brief, "recommendedSections", []) or []
        ]
        content_snippets = [_text(extraction.summary.positioningSummary)]
        detected_industry, industry_confidence = detect_industry(
            company_name=_text(lead.companyName),
            mission=_text(brief.companySummary.value),
            services=services_list,
            content_snippets=content_snippets,
        )
        logger.info(
            f"Detected industry: {detected_industry} (confidence: {industry_confidence:.2f})"
        )

        brand_tokens = _brand_tokens(
            palette_mode=palette_mode,
            theme=theme,
            brief=brief,
            extraction=extraction,
            refs=refs,
            industry=detected_industry,
        )
        hero = _hero_variant(brief=brief, extraction=extraction, theme=theme, refs=refs)
        sections = _section_stack(brief=brief, extraction=extraction, refs=refs)
        cta_strategy = _cta_strategy(brief=brief, extraction=extraction, refs=refs)

        # Apply content rewriting and creative copy generation (Phase 2)
        await lead_repository._update_job(
            job_id, progress=45, step="Enhancing content with creative copy"
        )

        from app.core.content_rewriter import rewrite_hero_section
        from app.core.creative_copy import (
            generate_creative_headline,
            generate_creative_cta,
        )

        brand_tone = (
            " ".join(extraction.summary.toneClues[:3]) or brief.toneProfile.value
        )
        content_enhancement_enabled = getattr(
            settings, "content_enhancement_enabled", True
        )

        if content_enhancement_enabled:
            try:
                # Option 1: LLM-based rewriting (more natural but requires LLM)
                rewritten_hero = await rewrite_hero_section(
                    hero_data={
                        "headline": hero.get("headline", ""),
                        "subheadline": hero.get("subheadline", ""),
                        "cta": cta_strategy.get("primaryCta", {}).get(
                            "label", "Get Started"
                        ),
                    },
                    industry=detected_industry,
                    company_name=_text(lead.companyName),
                    mission=_text(brief.companySummary.value),
                    brand_tone=brand_tone,
                )

                # Update hero with rewritten content
                if "headline" in rewritten_hero:
                    hero["headline"] = rewritten_hero["headline"]
                    hero["headline_rewrite_meta"] = rewritten_hero.get(
                        "headline_meta", {}
                    )

                if "subheadline" in rewritten_hero:
                    hero["subheadline"] = rewritten_hero["subheadline"]
                    hero["subheadline_rewrite_meta"] = rewritten_hero.get(
                        "subheadline_meta", {}
                    )

                if "cta" in rewritten_hero:
                    cta_strategy["primaryCta"]["label"] = rewritten_hero["cta"]
                    cta_strategy["primaryCta"]["rewrite_meta"] = rewritten_hero.get(
                        "cta_meta", {}
                    )

                logger.info(f"LLM content rewriting completed for {lead.companyName}")

            except Exception as e:
                logger.warning(
                    f"LLM rewriting failed: {e}, falling back to template-based generation"
                )

                # Option 2: Template-based creative copy (fast, no LLM needed)
                try:
                    creative_headline = await generate_creative_headline(
                        company_name=_text(lead.companyName),
                        mission=_text(brief.companySummary.value),
                        industry=detected_industry,
                        brand_tone=brand_tone,
                        positioning=_text(extraction.summary.positioningSummary),
                        prefer_bold=theme["name"] in ["editorial-frame", "color-study"],
                    )

                    creative_cta = await generate_creative_cta(
                        industry=detected_industry,
                        context="primary",
                        brand_tone=brand_tone,
                    )

                    # Use creative copy if confidence is high
                    if creative_headline.get("confidence", 0) >= 75:
                        hero["headline"] = creative_headline["headline"]
                        hero["creative_headline_meta"] = creative_headline

                    if creative_cta.get("confidence", 0) >= 80:
                        cta_strategy["primaryCta"]["label"] = creative_cta["text"]
                        cta_strategy["primaryCta"]["creative_cta_meta"] = creative_cta

                    logger.info(
                        f"Template-based creative copy completed for {lead.companyName}"
                    )

                except Exception as fallback_error:
                    logger.warning(
                        f"Creative copy generation also failed: {fallback_error}, using original content"
                    )
        else:
            logger.info("Content enhancement disabled, using original content")

        # Phase 3: Hero variant selection and configuration (new feature)
        await lead_repository._update_job(
            job_id, progress=47, step="Selecting hero variant and navigation"
        )

        from app.core.hero_variants import select_hero_variant, generate_hero_config
        from app.core.navigation import generate_navigation, add_scroll_behavior

        # Detect available assets for hero selection
        has_video = any(cue.assetType == "video" for cue in extraction.brandAssetCues)
        has_product_image = any(
            cue.assetType == "image" and "product" in cue.label.lower()
            for cue in extraction.brandAssetCues
        )
        has_multiple_images = (
            sum(1 for cue in extraction.brandAssetCues if cue.assetType == "image") >= 3
        )

        # Determine brand personality from tone
        tone_lower = brand_tone.lower() if brand_tone else ""
        if any(
            word in tone_lower for word in ["bold", "vibrant", "dynamic", "energetic"]
        ):
            brand_personality = "bold"
        elif any(
            word in tone_lower for word in ["minimal", "clean", "simple", "refined"]
        ):
            brand_personality = "minimal"
        elif any(
            word in tone_lower
            for word in ["creative", "innovative", "artistic", "experimental"]
        ):
            brand_personality = "creative"
        else:
            brand_personality = "professional"

        # Select best hero variant
        hero_variant_key, hero_variant_config = select_hero_variant(
            industry=detected_industry,
            has_video=has_video,
            has_product_image=has_product_image,
            has_multiple_images=has_multiple_images,
            brand_personality=brand_personality,
        )

        # Collect assets for hero config
        hero_assets = {}
        if has_video:
            video_cues = [
                c for c in extraction.brandAssetCues if c.assetType == "video"
            ]
            if video_cues:
                hero_assets["video_url"] = video_cues[0].value

        if has_product_image:
            product_images = [
                c
                for c in extraction.brandAssetCues
                if c.assetType == "image" and "product" in c.label.lower()
            ]
            if product_images:
                hero_assets["product_image"] = product_images[0].value

        if has_multiple_images:
            image_cues = [
                c for c in extraction.brandAssetCues if c.assetType == "image"
            ]
            hero_assets["carousel_images"] = [c.value for c in image_cues[:5]]
            hero_assets["mosaic_images"] = [c.value for c in image_cues[:8]]

        # Add hero image if available
        hero_image_cues = [
            c
            for c in extraction.brandAssetCues
            if c.assetType == "image"
            and any(
                keyword in c.label.lower()
                for keyword in ["hero", "banner", "background", "header"]
            )
        ]
        if hero_image_cues:
            hero_assets["hero_image"] = hero_image_cues[0].value
        elif has_multiple_images:
            # Use first available image as hero fallback
            image_cues = [
                c for c in extraction.brandAssetCues if c.assetType == "image"
            ]
            if image_cues:
                hero_assets["hero_image"] = image_cues[0].value

        # Generate complete hero configuration
        enhanced_hero_config = generate_hero_config(
            variant_key=hero_variant_key,
            headline=hero.get("headline", ""),
            subheadline=hero.get("subheadline", ""),
            cta_text=cta_strategy.get("primaryCta", {}).get("label", "Get Started"),
            cta_href=cta_strategy.get("primaryCta", {}).get("href", "#contact"),
            colors=brand_tokens.get("enhancedColorSystem", {}),
            assets=hero_assets,
        )

        # Merge enhanced hero config into hero object
        hero.update(
            {
                "variant_key": hero_variant_key,
                "variant_config": enhanced_hero_config,
                "variant_meta": {
                    "selection_reason": f"Selected {hero_variant_key} for {detected_industry} with {brand_personality} personality",
                    "has_video": has_video,
                    "has_product_image": has_product_image,
                    "brand_personality": brand_personality,
                },
            }
        )

        logger.info(f"Selected hero variant: {hero_variant_key} for {lead.companyName}")

        # Phase 4: Navigation generation
        logo_url = None
        logo_cues = [c for c in extraction.brandAssetCues if c.assetType == "logo"]
        if logo_cues:
            logo_url = logo_cues[0].value

        navigation_config = generate_navigation(
            sections=sections,
            industry=detected_industry,
            logo_url=logo_url,
            company_name=_text(lead.companyName),
            theme="dark" if palette_mode == "zinc" else "light",
        )

        # Add scroll behavior to navigation
        navigation_config = add_scroll_behavior(navigation_config)

        logger.info(
            f"Generated navigation with {len(navigation_config['items'])} items, style: {navigation_config['style']}"
        )

        # Phase 5: Awwwards pattern integration
        await lead_repository._update_job(
            job_id, progress=48, step="Loading Awwwards-inspired patterns"
        )

        from app.core.awwwards_patterns import (
            get_patterns_for_industry,
            get_hero_pattern_recommendation,
        )

        # Get relevant patterns for this industry
        awwwards_patterns = get_patterns_for_industry(detected_industry)
        logger.info(
            f"Loaded {len(awwwards_patterns)} Awwwards patterns for {detected_industry}"
        )

        # Get hero pattern recommendation based on assets
        hero_pattern_recommendation = get_hero_pattern_recommendation(
            industry=detected_industry,
            available_assets={
                "has_video": has_video,
                "has_product_image": has_product_image,
                "has_hero_images": bool(hero_image_cues),
            },
        )

        # Store pattern metadata for frontend usage
        pattern_metadata = {
            "industry": detected_industry,
            "pattern_count": len(awwwards_patterns),
            "hero_pattern_recommendation": {
                "name": hero_pattern_recommendation["name"],
                "description": hero_pattern_recommendation["description"],
            },
            "available_pattern_categories": list(
                set(p.get("category") for p in awwwards_patterns)
            ),
        }

        # Generate visual redesign brief (with pattern context)
        await lead_repository._update_job(
            job_id,
            progress=50,
            step="Generating visual redesign brief with pattern guidance",
        )

        from app.core.visual_redesign import generate_visual_redesign_brief

        visual_redesign_briefs = []
        if settings.visual_redesign_enabled:
            try:
                visual_redesign_briefs = await generate_visual_redesign_brief(
                    brief=brief,
                    extraction=extraction,
                    client_brand=brand_tokens,
                )
                logger.info(
                    f"Generated {len(visual_redesign_briefs)} redesign briefs with pattern guidance"
                )
                # Update brief with visual redesign
                await lead_repository.update_brief_visual_redesign(
                    lead_id=site_id,
                    visual_redesign_briefs=visual_redesign_briefs,
                )
            except Exception as e:
                logger.error(f"Visual redesign generation failed: {e}")
                visual_redesign_briefs = []

        missing_requirements = list(
            dict.fromkeys([*brief.missingRequirements, *extraction.gapItems])
        )
        if not extraction.brandAssetCues:
            missing_requirements.append("brand_assets_missing")
        if not extraction.sourceCitations:
            missing_requirements.append("source_citations_missing")
        if not brief.recommendedSections:
            missing_requirements.append("section_guidance_missing")
        if not _text(brief.conversionAngle.value):
            missing_requirements.append("cta_strategy_missing")
        missing_requirements = list(dict.fromkeys(missing_requirements))

        # Compute diversity score based on current batch
        batch_sites = [
            site
            for site in await self._list_sites(limit=50, offset=0)
            if site.id != site_id
        ]
        diversity_score = _compute_diversity_score(
            batch_sites, theme["themeKey"], palette_mode
        )

        quality_score = _quality_score(
            brief=brief,
            extraction=extraction,
            brand_tokens=brand_tokens,
            site_sections=sections,
            missing_requirements=missing_requirements,
            diversity_score=diversity_score,
            screenshot_qa_score=None,  # Will be updated after screenshot QA
        )
        readiness_status, qa_status = _readiness_status(
            brief, quality_score, missing_requirements
        )
        review_rubric = _review_rubric(
            brief=brief,
            extraction=extraction,
            site_sections=sections,
            brand_tokens=brand_tokens,
            palette_mode=palette_mode,
        )
        overrides = await self._site_overrides(site_id)
        # Apply operator overrides to generated baselines
        applied_sections = self._apply_overrides(sections, overrides)
        applied_hero = self._apply_hero_overrides(hero, overrides)
        applied_cta = self._apply_cta_overrides(cta_strategy, overrides)
        applied_tokens = self._apply_brand_overrides(brand_tokens, overrides)
        applied_palette = _text(applied_tokens["paletteMode"]) or palette_mode
        if applied_palette in {"zinc", "light", "colorful"}:
            palette_mode = applied_palette  # type: ignore[assignment]

        # Support explicit operator-selected theme override. If an override
        # sets `themeKey` or `theme.key`, prefer that theme for this
        # generation pass and recompute baselines before reapplying overrides.
        explicit_theme_key: str | None = None
        for ov in overrides:
            path = _text(ov.get("path"))
            val = _text(ov.get("value"))
            if path in ("themeKey", "theme.key") and val:
                explicit_theme_key = val
                break

        if explicit_theme_key:
            theme = _theme_data(explicit_theme_key)
            theme_rationale = f"Operator selected theme {theme['name']}"
            # Recompute baselines using the explicit theme and the (possibly) applied palette
            recomputed_brand_tokens = _brand_tokens(
                palette_mode=cast(PaletteMode, palette_mode),
                theme=theme,
                brief=brief,
                extraction=extraction,
                refs=refs,
            )
            recomputed_hero = _hero_variant(
                brief=brief, extraction=extraction, theme=theme, refs=refs
            )
            recomputed_sections = _section_stack(
                brief=brief, extraction=extraction, refs=refs
            )
            recomputed_cta = _cta_strategy(
                brief=brief, extraction=extraction, refs=refs
            )

            # Reapply overrides to the recomputed baselines so operator edits persist
            applied_sections = self._apply_overrides(recomputed_sections, overrides)
            applied_hero = self._apply_hero_overrides(recomputed_hero, overrides)
            applied_cta = self._apply_cta_overrides(recomputed_cta, overrides)
            applied_tokens = self._apply_brand_overrides(
                recomputed_brand_tokens, overrides
            )
            applied_palette = _text(applied_tokens["paletteMode"]) or palette_mode
            if applied_palette in {"zinc", "light", "colorful"}:
                palette_mode = applied_palette  # type: ignore[assignment]

            # Recompute diversity score with the new theme
            diversity_score = _compute_diversity_score(
                batch_sites, theme["themeKey"], cast(PaletteMode, palette_mode)
            )

        # Log final applied section stack before quality scoring / QA
        logger.info("Created %d site sections", len(applied_sections))
        for section in applied_sections:
            logger.info(
                "  - %s: kind=%s, componentId=%s",
                _text(section.get("title") or section.get("headline")),
                section.get("kind"),
                section.get("componentId"),
            )

        # Phase 6: Calculate quality metrics and uniqueness scores
        await lead_repository._update_job(
            job_id, progress=52, step="Calculating quality metrics"
        )

        from app.core.site_quality_metrics import calculate_overall_quality_score

        # Build site object for quality assessment
        site_for_quality = {
            "themeName": theme["name"],
            "heroVariant": hero_variant_key,
            "paletteMode": palette_mode,
            "colors": applied_tokens.get("enhancedColorSystem", {}),
            "typography": applied_tokens.get("typography", {}),
            "sections": applied_sections,
            "navigationConfig": navigation_config,
        }

        # Calculate comprehensive quality metrics
        quality_metrics = calculate_overall_quality_score(site_for_quality)
        logger.info(
            f"Quality metrics: overall={quality_metrics['overall_score']}, "
            f"grade={quality_metrics['grade']}, "
            f"color_diversity={quality_metrics['metrics']['color_diversity']['score']}, "
            f"animation_coverage={quality_metrics['metrics']['animation_coverage']['score']}"
        )

        # Store quality metrics in brand tokens for reference
        applied_tokens["qualityMetrics"] = quality_metrics

        quality_score = _quality_score(
            brief=brief,
            extraction=extraction,
            brand_tokens=applied_tokens,
            site_sections=applied_sections,
            missing_requirements=missing_requirements,
            diversity_score=diversity_score,
            screenshot_qa_score=None,  # Will be updated after screenshot QA
        )
        review_rubric = _review_rubric(
            brief=brief,
            extraction=extraction,
            site_sections=applied_sections,
            brand_tokens=applied_tokens,
            palette_mode=cast(PaletteMode, palette_mode),
        )
        comparison_entries = _comparison_entries(
            brief=brief,
            theme=theme,
            palette_mode=cast(PaletteMode, palette_mode),
            hero=applied_hero,
            sections=applied_sections,
            cta_strategy=applied_cta,
            brand_tokens=applied_tokens,
        )

        now = _now()

        # Generate friendly preview slug from company name
        database = get_database()
        existing_slugs: set[str] = set()
        if database is not None:
            cursor = database["generated_sites"].find({}, {"previewSlug": 1})
            # Handle both real MongoDB cursor and mock cursor
            try:
                async for doc in cursor:  # type: ignore[attr-defined]
                    if slug := doc.get("previewSlug"):
                        existing_slugs.add(slug)
            except TypeError:
                # Mock cursor doesn't support async iteration, use to_list
                if hasattr(cursor, "to_list"):
                    docs = await cursor.to_list(length=None)
                    for doc in docs:
                        if slug := doc.get("previewSlug"):
                            existing_slugs.add(slug)
        else:
            # In-memory mode: get from self._sites
            async with self._memory_lock:
                for doc in self._sites.values():
                    if slug := doc.get("previewSlug"):
                        existing_slugs.add(slug)

        company_name_for_slug = _text(lead.companyName) or "site"
        logger.info(
            "Generating friendly slug from company name: %s (existing slugs count: %d)",
            company_name_for_slug,
            len(existing_slugs),
        )
        friendly_slug = _generate_friendly_slug(company_name_for_slug, existing_slugs)
        logger.info("Generated friendly slug: %s", friendly_slug)

        # Compute layout hash for duplicate detection
        temp_site = GeneratedSite(
            id=site_id,
            leadId=site_id,
            generationJobId=job_id,
            briefId=brief.id,
            briefVersion=brief.version,
            version=next_version,
            themeId=theme["id"],
            themeKey=theme["themeKey"],
            themeName=theme["name"],
            themeRationale=theme_rationale,
            paletteMode=cast(PaletteMode, palette_mode),
            paletteRationale=palette_rationale,
            brandTokens=BrandTokens.model_validate(applied_tokens),
            heroVariant=HeroVariant.model_validate(applied_hero),
            sectionStack=[SiteSection.model_validate(s) for s in applied_sections],
            ctaStrategy=CtaStrategy.model_validate(applied_cta),
            navigationConfig=navigation_config,
            awwwardsPatternMetadata=pattern_metadata,
            qualityScore=0,
            readinessStatus="blocked",
            qaStatus="fail",
            reviewRubric=[],
            comparisonEntries=[],
            sourceTraceability=[],
            missingRequirements=[],
            sourceAttribution=None,
            browserReviewState="not_reviewed",
            publishApprovalState="pending",
            screenshotRefs=[],
            latestReviewId=None,
            handoffRecordId=None,
            diversityNotes=[],
            diversityScore=diversity_score,
            layoutHash="",
            previewSlug=friendly_slug,
            previewUrl=f"/st/{friendly_slug}",
            overrideCount=len(overrides),
            overrides=[],
            exportMetadata=None,
            createdAt=now,
            updatedAt=now,
            publishedAt=None,
        )
        layout_hash = self._screenshot_comparator.compute_layout_hash(temp_site)

        # Validate generated copy for client-safety: no blocked/internal phrases
        settings = get_settings()
        blocked = [
            p.strip().lower()
            for p in (settings.cta_blocked_phrases or "").split(",")
            if p.strip()
        ]
        violations: list[str] = []
        # check CTA labels
        for key, action in (applied_cta or {}).items():
            label = _text(action.get("label") if isinstance(action, dict) else action)
            lowered = label.lower()
            for phrase in blocked:
                if phrase and phrase in lowered:
                    violations.append(f"cta.{key}:{phrase}")
        # check section bodies
        for idx, sec in enumerate(applied_sections or []):
            body = _text(sec.get("body"))
            lowered = body.lower()
            for phrase in blocked:
                if phrase and phrase in lowered:
                    violations.append(f"section.{idx}:{phrase}")
        if violations:
            raise ValueError(f"blocked_language_found:{','.join(violations)}")

        # AI Generation (Phase 3) - Generate TSX code if master brief is approved
        ai_generation_result: dict[str, Any] | None = None
        if use_ai_generation and master_brief:
            logger.info("Starting AI-native code generation for site %s", site_id)
            await lead_repository._update_job(  # noqa: SLF001
                job_id, progress=55, step="Generating landing page code with AI"
            )

            try:
                from app.core.ai_site_generation import generate_with_retry

                ai_generation_result = await generate_with_retry(
                    master_brief=master_brief,
                    extraction=extraction,
                    site_id=site_id,
                    max_retries=3,
                )

                if ai_generation_result["success"]:
                    logger.info(
                        f"AI generation successful: compiled to {ai_generation_result.get('compiledBundleUrl')}"
                    )
                else:
                    logger.warning(
                        f"AI generation failed: {ai_generation_result.get('error')}. "
                        "Continuing with deterministic sections."
                    )

            except Exception as e:
                logger.error(f"AI generation error: {e}", exc_info=True)
                ai_generation_result = None

        version_id = uuid4().hex

        def _screenshot_ref_docs(
            current_site: GeneratedSite | None,
        ) -> list[dict[str, Any]]:
            """Return screenshotRefs as plain dicts for persistence.

            GeneratedSite.screenshotRefs is a list of SiteScreenshotMetadata models in
            memory, but Mongo/mongomock expect plain dicts. When copying from a
            previous version, convert any models back to primitive dicts.
            """

            if current_site is None:
                return []
            refs = getattr(current_site, "screenshotRefs", []) or []
            docs: list[dict[str, Any]] = []
            for item in refs:
                if hasattr(item, "model_dump"):
                    docs.append(item.model_dump())
                else:
                    docs.append(dict(item))
            return docs

        version_doc = {
            "id": version_id,
            "siteId": site_id,
            "leadId": site_id,
            "generationJobId": job_id,
            "version": next_version,
            "briefId": brief.id,
            "briefVersion": brief.version,
            "themeId": theme["id"],
            "themeKey": theme["themeKey"],
            "themeName": theme["name"],
            "themeRationale": theme_rationale,
            "paletteMode": palette_mode,
            "paletteRationale": palette_rationale,
            "brandTokens": applied_tokens,
            "heroVariant": applied_hero,
            "sectionStack": applied_sections,
            "ctaStrategy": applied_cta,
            "navigationConfig": navigation_config,
            "qualityScore": quality_score,
            "readinessStatus": readiness_status,
            "qaStatus": qa_status,
            "reviewRubric": review_rubric,
            "comparisonEntries": comparison_entries,
            "sourceTraceability": refs[:8],
            "missingRequirements": missing_requirements,
            "sourceAttribution": _site_source_attribution(
                lead=lead,
                brief=brief,
                extraction=extraction,
                theme=theme,
                palette_mode=cast(PaletteMode, palette_mode),
            ),
            "browserReviewState": _review_state_from(current),
            "publishApprovalState": _publish_approval_state(
                current, _review_state_from(current), missing_requirements
            ),
            "screenshotRefs": _screenshot_ref_docs(current),
            "latestReviewId": current.latestReviewId if current else None,
            "handoffRecordId": current.handoffRecordId if current else None,
            "diversityNotes": _diversity_notes(
                current, theme, cast(PaletteMode, palette_mode), refs
            ),
            "diversityScore": diversity_score,
            "layoutHash": layout_hash,
            "previewSlug": current.previewSlug if current else friendly_slug,
            "previewUrl": f"/st/{current.previewSlug if current else friendly_slug}",
            "overrideCount": len(overrides),
            "refinementPromptId": refinement_prompt_id,
            "createdAt": now,
            "updatedAt": now,
            # Auto-publish sites that meet quality threshold
            "publishedAt": now if readiness_status == "ready_to_publish" else None,
            # AI generation fields (Phase 3)
            "sourceCode": ai_generation_result.get("sourceCode")
            if ai_generation_result and "sourceCode" in ai_generation_result
            else None,
            "compiledBundleUrl": ai_generation_result.get("compiledBundleUrl")
            if ai_generation_result and "compiledBundleUrl" in ai_generation_result
            else None,
            "compilationStatus": ai_generation_result.get(
                "compilationStatus", "pending"
            )
            if ai_generation_result
            else None,
            "compilationError": ai_generation_result.get("error")
            if ai_generation_result and "error" in ai_generation_result
            else None,
        }
        site_doc = {
            "id": site_id,
            "leadId": site_id,
            "generationJobId": job_id,
            "briefId": brief.id,
            "briefVersion": brief.version,
            "version": next_version,
            "themeId": theme["id"],
            "themeKey": theme["themeKey"],
            "themeName": theme["name"],
            "themeRationale": theme_rationale,
            "paletteMode": palette_mode,
            "paletteRationale": palette_rationale,
            "brandTokens": applied_tokens,
            "heroVariant": applied_hero,
            "sectionStack": applied_sections,
            "ctaStrategy": applied_cta,
            "navigationConfig": navigation_config,
            "qualityScore": quality_score,
            "readinessStatus": readiness_status,
            "qaStatus": qa_status,
            "reviewRubric": review_rubric,
            "comparisonEntries": comparison_entries,
            "sourceTraceability": refs[:8],
            "missingRequirements": missing_requirements,
            "sourceAttribution": _site_source_attribution(
                lead=lead,
                brief=brief,
                extraction=extraction,
                theme=theme,
                palette_mode=cast(PaletteMode, palette_mode),
            ),
            "browserReviewState": _review_state_from(current),
            "publishApprovalState": _publish_approval_state(
                current, _review_state_from(current), missing_requirements
            ),
            "screenshotRefs": _screenshot_ref_docs(current),
            "latestReviewId": current.latestReviewId if current else None,
            "handoffRecordId": current.handoffRecordId if current else None,
            "diversityNotes": _diversity_notes(
                current, theme, cast(PaletteMode, palette_mode), refs
            ),
            "diversityScore": diversity_score,
            "layoutHash": layout_hash,
            "previewSlug": current.previewSlug if current else friendly_slug,
            "previewUrl": f"/sites/{current.previewSlug if current else friendly_slug}",
            "overrideCount": len(overrides),
            "overrides": overrides,
            "exportMetadata": None,
            "refinementPromptId": refinement_prompt_id,
            "isManuallyRefined": bool(refinement_prompt_id),
            "createdAt": current.createdAt if current else now,
            "updatedAt": now,
            # Auto-publish sites that meet quality threshold
            "publishedAt": now if readiness_status == "ready_to_publish" else None,
            # AI generation fields (Phase 3)
            "sourceCode": ai_generation_result.get("sourceCode")
            if ai_generation_result and "sourceCode" in ai_generation_result
            else None,
            "compiledBundleUrl": ai_generation_result.get("compiledBundleUrl")
            if ai_generation_result and "compiledBundleUrl" in ai_generation_result
            else None,
            "compilationStatus": ai_generation_result.get(
                "compilationStatus", "pending"
            )
            if ai_generation_result
            else None,
            "compilationError": ai_generation_result.get("error")
            if ai_generation_result and "error" in ai_generation_result
            else None,
        }

        # Run screenshot QA if enabled
        settings = get_settings()
        screenshot_qa_result: dict[str, Any] | None = None
        if settings.visual_redesign_enabled:
            try:
                logger.info("Starting screenshot QA for %s", site_id)
                await lead_repository._update_job(  # noqa: SLF001
                    job_id,
                    progress=80,
                    step="Capturing and analyzing preview screenshot",
                )
                from app.core.screenshot_analyzer import get_screenshot_analyzer

                analyzer = get_screenshot_analyzer()
                section_names_for_qa: list[str] = []
                for idx, section in enumerate(applied_sections):
                    title = _text(
                        section.get("title")
                        or section.get("headline")
                        or section.get("kind")
                        or f"Section {idx + 1}"
                    )
                    if title:
                        section_names_for_qa.append(title)

                screenshot_qa_result = (
                    await self._screenshot_comparator.compare_layout_screenshot(
                        site_id=site_id,
                        preview_url=f"/st/{friendly_slug}",
                        section_names=section_names_for_qa,
                    )
                )

                if screenshot_qa_result.get("success"):
                    # Update quality score based on screenshot QA (visual quality is primary)
                    screenshot_quality = screenshot_qa_result.get(
                        "qualityScore", quality_score
                    )
                    logger.info(
                        "Screenshot QA completed for %s: quality_score=%s",
                        site_id,
                        screenshot_quality,
                    )

                    # Recompute quality score using screenshot QA as the primary visual score
                    quality_score = _quality_score(
                        brief=brief,
                        extraction=extraction,
                        brand_tokens=applied_tokens,
                        site_sections=applied_sections,
                        missing_requirements=missing_requirements,
                        diversity_score=diversity_score,
                        screenshot_qa_score=screenshot_quality,
                    )

                    # Create screenshot metadata record
                    screenshot_meta = {
                        "id": uuid4().hex,
                        "label": "Generated preview screenshot",
                        "url": screenshot_qa_result.get("desktopScreenshotUrl", ""),
                        "capturedAt": _now(),
                        "width": 1440,
                        "height": None,  # Full-page, so height varies
                        "contentHash": screenshot_qa_result.get("layoutHash", ""),
                        "notes": screenshot_qa_result.get("readinessAssessment", ""),
                    }

                    site_doc["screenshotRefs"] = [screenshot_meta]
                    version_doc["screenshotRefs"] = [screenshot_meta]

                    # Always use the recomputed quality score (visual quality + data completeness)
                    site_doc["qualityScore"] = quality_score
                    version_doc["qualityScore"] = quality_score

                    # Recompute readiness/qa status based on new quality score
                    readiness_status, qa_status = _readiness_status(
                        brief, quality_score, missing_requirements
                    )
                    site_doc["readinessStatus"] = readiness_status
                    site_doc["qaStatus"] = qa_status
                    version_doc["readinessStatus"] = readiness_status
                    version_doc["qaStatus"] = qa_status

                    # If quality is below threshold but within iteration budget, generate improvement
                    if (
                        screenshot_quality < settings.visual_redesign_quality_threshold
                        and next_version < settings.visual_redesign_max_iterations
                    ):
                        try:
                            await lead_repository._update_job(  # noqa: SLF001
                                job_id,
                                progress=85,
                                step="Generating improvement recommendations",
                            )
                            section_names = [
                                s.get("title", "Section") for s in applied_sections
                            ]
                            brand_summary = json.dumps(
                                {
                                    "paletteMode": applied_tokens.get("paletteMode"),
                                    "primaryColor": applied_tokens.get(
                                        "primaryColor", {}
                                    ).get("value"),
                                },
                                default=str,
                            )

                            improvement_brief = await analyzer.generate_improvement_brief(
                                site_id=site_id,
                                extraction_summary=extraction.summary.positioningSummary
                                or "",
                                section_stack=section_names,
                                qa_critique=screenshot_qa_result.get("rawCritique", ""),
                                brand_summary=brand_summary,
                            )

                            # Store improvement recommendations for next iteration
                            site_doc["improvementRecommendations"] = improvement_brief
                            version_doc["improvementRecommendations"] = (
                                improvement_brief
                            )
                        except Exception as e:
                            logger.warning(
                                f"Improvement brief generation failed for {site_id}: {e}"
                            )
                else:
                    logger.warning(
                        f"Screenshot QA failed for {site_id}: {screenshot_qa_result.get('error')}"
                    )
                    # Ensure every section still has a componentId even if QA fails
                    for section in applied_sections:
                        if not section.get("componentId"):
                            mapped = _map_section_kind_to_component_id(
                                section.get("kind", "") or section.get("title", "")
                            )
                            section["componentId"] = mapped
                            logger.info(
                                "Mapped section '%s' to componentId: %s (QA fallback)",
                                _text(section.get("title") or section.get("headline")),
                                mapped,
                            )
                    site_doc["sectionStack"] = applied_sections
                    version_doc["sectionStack"] = applied_sections
            except Exception as e:
                logger.error(
                    "Screenshot QA integration failed for %s: %s",
                    site_id,
                    e,
                    exc_info=True,
                )
                # FALLBACK: make sure sections still have reasonable componentIds
                for section in applied_sections:
                    if not section.get("componentId"):
                        mapped = _map_section_kind_to_component_id(
                            section.get("kind", "") or section.get("title", "")
                        )
                        section["componentId"] = mapped
                        logger.info(
                            "Mapped section '%s' to componentId: %s (exception fallback)",
                            _text(section.get("title") or section.get("headline")),
                            mapped,
                        )
                site_doc["sectionStack"] = applied_sections
                version_doc["sectionStack"] = applied_sections

        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._sites[site_id] = site_doc
                self._versions.setdefault(site_id, []).append(version_doc)
                self._overrides.setdefault(site_id, overrides)
                self._reviews.setdefault(site_id, self._reviews.get(site_id, {}))
        else:
            await database["generated_site_versions"].insert_one(version_doc)
            if current is None:
                await database["generated_sites"].insert_one(site_doc)
            else:
                await database["generated_sites"].replace_one(
                    {"id": site_id}, site_doc, upsert=True
                )
        completed_step = (
            "Preview generated" if current is None else "Preview republished"
        )
        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            status="completed",
            progress=100,
            step=completed_step,
            finished=True,
            lead_ids=[site_id],
            metadata={
                "siteId": site_id,
                "leadId": site_id,
                "briefId": brief.id,
                "briefVersion": brief.version,
                "version": next_version,
                "screenshotQA": screenshot_qa_result,
            },
        )

        logger.info("Final quality score for %s: %s", site_id, site_doc["qualityScore"])
        logger.info("=== Site generation complete for %s ===", site_id)

        # If this run was triggered by a refinement prompt, update the prompt record
        # with the resulting version and quality outcome.
        if refinement_prompt_id:
            prompt_status = "success"
            failure_reason: str | None = None
            if qa_status != "pass" or readiness_status in {"blocked", "needs_review"}:
                prompt_status = "failed"
                failure_reason = "quality_below_threshold"

            await self.update_prompt_result(
                site_id=site_id,
                prompt_id=refinement_prompt_id,
                version_id=version_id,
                quality_score=site_doc["qualityScore"],
                status=prompt_status,
                failure_reason=failure_reason,
            )
        return _site_doc_to_current(site_doc)

    async def _dispatch_generation_job(
        self, *, site_id: str, job_id: str, request: SiteGenerateRequest | None
    ) -> None:
        settings = get_settings()
        if settings.celery_task_always_eager:
            try:
                await self.run_generation_job(
                    site_id=site_id, job_id=job_id, request=request
                )
                await self._maybe_queue_auto_iteration(
                    site_id=site_id, job_id=job_id, request=request
                )
            except Exception:  # pragma: no cover - eager path logging
                logging.getLogger("lenquant.jobs").exception(
                    "Inline job generation:%s:%s failed", site_id, job_id
                )
                raise
            return

        from app.core.tasks import run_site_generation_job_task

        payload = request.model_dump() if request else None
        run_site_generation_job_task.delay(  # type: ignore[attr-defined]
            site_id=site_id, job_id=job_id, request_payload=payload
        )

    async def republish_site(self, site_id: str) -> GeneratedSite | None:
        return await self.generate_site(site_id)

    async def add_export_metadata(
        self, site_id: str, export_metadata: SiteExportMetadata
    ) -> SiteExportMetadata | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        database = get_database()
        # Initialize sync status as synced if not provided
        if (
            not hasattr(export_metadata, "exportSyncStatus")
            or export_metadata.exportSyncStatus is None
        ):
            export_metadata.exportSyncStatus = "synced"
        export_record = {
            "id": uuid4().hex,
            "siteId": site_id,
            **export_metadata.model_dump(),
        }
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["exportMetadata"] = export_metadata.model_dump()
                    doc["updatedAt"] = _now()
                self._exports.setdefault(site_id, []).append(export_record)
                await analytics_repository.record_admin_event(
                    event_type="site_export_created",
                    event_name=f"{export_metadata.exportType} export recorded",
                    site_id=site.id,
                    lead_id=site.leadId,
                    metadata={
                        "exportType": export_metadata.exportType,
                        "destination": export_metadata.repoUrl,
                    },
                )
                return export_metadata
        await database["site_exports"].insert_one(export_record)
        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "exportMetadata": export_metadata.model_dump(),
                    "updatedAt": _now(),
                }
            },
        )
        await analytics_repository.record_admin_event(
            event_type="site_export_created",
            event_name=f"{export_metadata.exportType} export recorded",
            site_id=site.id,
            lead_id=site.leadId,
            metadata={
                "exportType": export_metadata.exportType,
                "destination": export_metadata.repoUrl,
            },
        )
        return export_metadata

    async def mark_export_out_of_sync(
        self, site_id: str, export_id: str, reason: str
    ) -> SiteExportMetadata | None:
        """
        Marks an export as out of sync and records the reason.

        Sets exportSyncStatus to "out_of_sync", records a timestamp,
        and adds a note explaining why.
        """
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None or site.exportMetadata is None:
            return None

        now = _now()
        updated_metadata = site.exportMetadata.model_copy()
        updated_metadata.exportSyncStatus = "out_of_sync"
        updated_metadata.lastSyncedAt = None
        updated_metadata.notes = f"{updated_metadata.notes or ''} [OUT OF SYNC: {reason} at {now.isoformat()}]".strip()
        updated_metadata.updatedAt = now

        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["exportMetadata"] = updated_metadata.model_dump()
                    doc["updatedAt"] = now
                return updated_metadata

        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "exportMetadata": updated_metadata.model_dump(),
                    "updatedAt": now,
                }
            },
        )
        return updated_metadata

    async def sync_export_edits(
        self, site_id: str, export_id: str, edits: list[dict[str, Any]]
    ) -> list[SiteOverrideRecord]:
        """
        Converts local edits into structured override records.

        Accepts a payload of local edits (path, value pairs),
        converts them into structured override records,
        updates the export's syncStatus back to "synced",
        and returns the created override records.
        """
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return []

        now = _now()
        created_overrides: list[SiteOverrideRecord] = []

        for edit in edits:
            path = edit.get("path", "").strip()
            value = edit.get("value", "").strip()
            reason = edit.get("reason", "Local edit synced from export").strip()

            if not path or not value:
                continue

            record = SiteOverrideRecord(
                id=uuid4().hex,
                siteId=site.id,
                leadId=site.leadId,
                version=site.version,
                scope="copy",  # Default to copy scope for local edits
                path=path,
                value=value,
                previousValue=None,  # We don't have the previous value for local edits
                reason=reason,
                sourceType="manual",
                status="active",
                createdBy="export_sync",
                createdAt=now,
                updatedAt=now,
            )
            created_overrides.append(record)

        # Save the new overrides
        database = get_database()
        if database is None:
            async with self._memory_lock:
                for record in created_overrides:
                    self._overrides.setdefault(site_id, []).append(record.model_dump())
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["overrides"] = list(self._overrides.get(site_id, []))
                    doc["overrideCount"] = len(doc["overrides"])
                    doc["updatedAt"] = now
        else:
            for record in created_overrides:
                await database["site_overrides"].insert_one(record.model_dump())
            await database["generated_sites"].update_one(
                {"id": site_id},
                {
                    "$set": {
                        "overrideCount": site.overrideCount + len(created_overrides),
                        "updatedAt": now,
                    },
                    "$push": {
                        "overrides": {
                            "$each": [r.model_dump() for r in created_overrides]
                        }
                    },
                },
            )

        # Update export sync status back to synced
        if site.exportMetadata:
            updated_metadata = site.exportMetadata.model_copy()
            updated_metadata.exportSyncStatus = "synced"
            updated_metadata.lastSyncedAt = now
            updated_metadata.updatedAt = now

            if database is None:
                async with self._memory_lock:
                    doc = self._sites.get(site_id)
                    if doc is not None:
                        doc["exportMetadata"] = updated_metadata.model_dump()
                        doc["updatedAt"] = now
            else:
                await database["generated_sites"].update_one(
                    {"id": site_id},
                    {
                        "$set": {
                            "exportMetadata": updated_metadata.model_dump(),
                            "updatedAt": now,
                        }
                    },
                )

        return created_overrides

    async def disable_override(
        self, site_id: str, override_id: str, *, actor: str | None = None
    ) -> SiteOverrideRecord | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        database = get_database()
        now = _now()
        if database is None:
            async with self._memory_lock:
                overrides = self._overrides.get(site_id, [])
                for override in overrides:
                    if override.get("id") == override_id:
                        override["status"] = "disabled"
                        override["updatedAt"] = now
                        doc = self._sites.get(site_id)
                        if doc is not None:
                            active = [
                                item
                                for item in overrides
                                if item.get("status") == "active"
                            ]
                            doc["overrides"] = active
                            doc["overrideCount"] = len(active)
                            doc["updatedAt"] = now
                        await analytics_repository.record_admin_event(
                            event_type="site_override_disabled",
                            event_name=f"Override {override_id} disabled",
                            site_id=site_id,
                            lead_id=site.leadId,
                            metadata={
                                "overrideId": override_id,
                                "actor": actor or "system",
                            },
                        )
                        return SiteOverrideRecord.model_validate(override)
                return None
        doc = await database["site_overrides"].find_one(
            {"id": override_id, "siteId": site_id}
        )
        if doc is None:
            return None
        if doc.get("status") == "disabled":
            return SiteOverrideRecord.model_validate(doc)
        await database["site_overrides"].update_one(
            {"id": override_id, "siteId": site_id},
            {"$set": {"status": "disabled", "updatedAt": now}},
        )
        updated = await database["site_overrides"].find_one(
            {"id": override_id, "siteId": site_id}
        )
        active_overrides = await self._site_overrides(site_id)
        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "overrides": active_overrides,
                    "overrideCount": len(active_overrides),
                    "updatedAt": now,
                }
            },
        )
        await analytics_repository.record_admin_event(
            event_type="site_override_disabled",
            event_name=f"Override {override_id} disabled",
            site_id=site_id,
            lead_id=site.leadId,
            metadata={"overrideId": override_id, "actor": actor or "system"},
        )
        return SiteOverrideRecord.model_validate(updated)

    async def list_export_history(self, site_id: str) -> list[SiteExportRecord]:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                records = self._exports.get(site_id, [])
                return [
                    SiteExportRecord.model_validate(record)
                    for record in sorted(
                        records, key=lambda item: item["createdAt"], reverse=True
                    )
                ]
        cursor = (
            database["site_exports"].find({"siteId": site_id}).sort("createdAt", -1)
        )
        docs = await cursor.to_list(length=None)
        return [SiteExportRecord.model_validate(doc) for doc in docs]

    async def build_export_bundle(self, site_id: str) -> tuple[str, bytes] | None:
        site = await self.get_site(site_id)
        if site is None:
            return None
        html = _export_html(site)
        css = _export_css(site)
        manifest = json.dumps(site.model_dump(mode="json"), default=str, indent=2)
        buffer = BytesIO()
        filename = f"{site.previewSlug or site.id}-bundle.zip"
        with zipfile.ZipFile(
            buffer, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as bundle:
            bundle.writestr("index.html", html)
            bundle.writestr("styles.css", css)
            bundle.writestr("site.json", manifest)
        return filename, buffer.getvalue()

    async def _get_review_doc(self, site_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return self._reviews.get(site_id)
        return await database["site_reviews"].find_one({"siteId": site_id})

    async def _apply_review_to_site(
        self, site_id: str, review_doc: dict[str, Any]
    ) -> None:
        now = _now()
        database = get_database()
        review_state = _review_state_from(None, review_doc)
        publish_state = (
            "blocked"
            if review_doc.get("blockedReason") or review_doc.get("outcome") == "fail"
            else ("approved" if review_doc.get("outcome") == "pass" else "pending")
        )
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc is None:
                    return
                doc["browserReviewState"] = review_state
                doc["publishApprovalState"] = publish_state
                doc["latestReviewId"] = review_doc.get("id")
                doc["screenshotRefs"] = list(review_doc.get("screenshots", []))
                doc["updatedAt"] = now
            return
        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "browserReviewState": review_state,
                    "publishApprovalState": publish_state,
                    "latestReviewId": review_doc.get("id"),
                    "screenshotRefs": review_doc.get("screenshots", []),
                    "updatedAt": now,
                }
            },
        )

    def _handoff_doc_for_site(
        self, site: GeneratedSite, review_doc: dict[str, Any] | None
    ) -> dict[str, Any]:
        review_state = _review_state_from(site, review_doc)
        publish_state = _publish_approval_state(
            site, review_state, list(site.missingRequirements)
        )
        review_checklist = list(review_doc.get("checklist", [])) if review_doc else []
        screenshots = (
            list(review_doc.get("screenshots", []))
            if review_doc
            else list(site.screenshotRefs)
        )
        status = (
            "ready"
            if publish_state == "approved"
            and review_state == "approved"
            and not site.missingRequirements
            else "blocked"
        )
        return {
            "id": site.handoffRecordId or uuid4().hex,
            "siteId": site.id,
            "leadId": site.leadId,
            "version": site.version,
            "status": status,
            "sourceAttribution": site.sourceAttribution.model_dump()  # type: ignore[union-attr]
            if site.sourceAttribution and hasattr(site.sourceAttribution, "model_dump")
            else site.sourceAttribution,
            "previewSlug": site.previewSlug,
            "previewUrl": site.previewUrl,
            "themeKey": site.themeKey,
            "paletteMode": site.paletteMode,
            "qualityScore": site.qualityScore,
            "readinessStatus": site.readinessStatus,
            "qaStatus": site.qaStatus,
            "publishApprovalState": publish_state,
            "reviewRecordId": review_doc.get("id")
            if review_doc
            else site.latestReviewId,
            "reviewOutcome": review_doc.get("outcome") if review_doc else None,
            "reviewChecklist": review_checklist,
            "screenshots": screenshots,
            "sourceTraceability": list(site.sourceTraceability),
            "missingRequirements": list(site.missingRequirements),
            "exportMetadata": site.exportMetadata.model_dump()
            if site.exportMetadata
            else None,
            "createdAt": site.createdAt,
            "updatedAt": _now(),
        }

    async def list_sites(
        self, *, limit: int = 25, offset: int = 0
    ) -> list[GeneratedSite]:
        return await self._list_sites(limit=limit, offset=offset)

    async def _list_sites(self, *, limit: int, offset: int) -> list[GeneratedSite]:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = list(self._sites.values())
                docs.sort(key=lambda item: item.get("updatedAt", _now()), reverse=True)
                return [
                    _site_doc_to_current(doc) for doc in docs[offset : offset + limit]
                ]
        cursor = (
            database["generated_sites"]
            .find({})
            .sort("updatedAt", -1)
            .skip(offset)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [_site_doc_to_current(doc) for doc in docs]

    async def _count_sites(self) -> int:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return len(self._sites)
        return await database["generated_sites"].count_documents({})

    async def _site_overrides(self, site_id: str) -> list[dict[str, Any]]:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return [
                    dict(item)
                    for item in self._overrides.get(site_id, [])
                    if item.get("status", "active") == "active"
                ]
        cursor = (
            database["site_overrides"]
            .find({"siteId": site_id, "status": "active"})
            .sort("createdAt", 1)
        )
        docs = await cursor.to_list(length=100)
        return [dict(doc) for doc in docs]

    def _apply_overrides(
        self, sections: list[dict[str, Any]], overrides: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        updated_sections = [dict(section) for section in sections]
        for override in overrides:
            path = _text(override.get("path"))
            value = _text(override.get("value"))
            if not path or not value:
                continue
            if path == "palette.mode":
                continue
            if path == "hero.headline" and updated_sections:
                continue
            if path.startswith("sections."):
                match = re.match(
                    r"sections\.(\d+)\.(title|headline|body|ctaLabel|eyebrow)", path
                )
                if match:
                    index = int(match.group(1))
                    field = match.group(2)
                    if 0 <= index < len(updated_sections):
                        updated_sections[index][field] = value
            elif path == "cta.primary.label" and updated_sections:
                updated_sections[-1]["ctaLabel"] = value
        return updated_sections

    def _apply_hero_overrides(
        self, hero: dict[str, Any], overrides: list[dict[str, Any]]
    ) -> dict[str, Any]:
        updated = dict(hero)
        for override in overrides:
            path = _text(override.get("path"))
            value = _text(override.get("value"))
            if path == "hero.headline" and value:
                updated["headline"] = value
            elif path == "hero.subheadline" and value:
                updated["subheadline"] = value
            elif path == "hero.supportingLine" and value:
                updated["supportingLine"] = value
            elif path == "hero.primaryCta" and value:
                updated["primaryCta"] = value
            elif path == "hero.secondaryCta" and value:
                updated["secondaryCta"] = value
        return updated

    def _apply_cta_overrides(
        self, cta_strategy: dict[str, Any], overrides: list[dict[str, Any]]
    ) -> dict[str, Any]:
        updated = {key: dict(value) for key, value in cta_strategy.items()}
        for override in overrides:
            path = _text(override.get("path"))
            value = _text(override.get("value"))
            if path == "cta.primary.label" and value:
                updated["primary"]["label"] = value
            elif path == "cta.secondary.label" and value:
                updated["secondary"]["label"] = value
            elif path == "cta.footer.label" and value:
                updated["footer"]["label"] = value
            elif path == "cta.primary.href" and value:
                updated["primary"]["href"] = value
            elif path == "cta.secondary.href" and value:
                updated["secondary"]["href"] = value
            elif path == "cta.footer.href" and value:
                updated["footer"]["href"] = value
        return updated

    def _apply_brand_overrides(
        self, brand_tokens: dict[str, Any], overrides: list[dict[str, Any]]
    ) -> dict[str, Any]:
        updated = {
            key: (dict(value) if isinstance(value, dict) else value)
            for key, value in brand_tokens.items()
        }
        for override in overrides:
            path = _text(override.get("path"))
            value = _text(override.get("value"))
            if path == "palette.mode" and value in {"zinc", "light", "colorful"}:
                updated["paletteMode"] = value
            elif path == "brand.primaryColor" and value:
                updated["primaryColor"]["value"] = value
            elif path == "brand.secondaryColor" and value:
                updated["secondaryColor"]["value"] = value
            elif path == "brand.accentColor" and value:
                updated["accentColor"]["value"] = value
            elif path == "brand.typography" and value:
                updated["typography"]["value"] = value
        return updated


site_repository = SiteRepository()


def _export_html(site: GeneratedSite) -> str:
    primary = site.ctaStrategy.primary
    secondary = site.ctaStrategy.secondary
    footer = site.ctaStrategy.footer
    hero = site.heroVariant
    sections_html = "\n".join(_section_html(section) for section in site.sectionStack)
    source_cards = (
        "\n".join(
            f"""
        <div class='source-card'>
            <div class='source-kind'>{_escape(reference.kind)}</div>
            <div class='source-label'>{_escape(reference.label)}</div>
            <div class='source-url'>{_escape(reference.sourceUrl)}</div>
        </div>
        """
            for reference in site.sourceTraceability[:6]
        )
        or "<p class='muted'>No traceability references provided.</p>"
    )
    return f"""<!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='utf-8' />
        <meta name='viewport' content='width=device-width, initial-scale=1' />
        <title>{_escape(hero.headline)}</title>
        <link rel='stylesheet' href='./styles.css' />
    </head>
    <body>
        <header class='hero'>
            <p class='eyebrow'>Preview slug {_escape(site.previewSlug)}</p>
            <h1>{_escape(hero.headline)}</h1>
            <p class='supported'>{_escape(hero.supportingLine)}</p>
            <div class='cta-row'>
                <a class='btn primary' href='{_escape(primary.href)}'>{_escape(primary.label)}</a>
                <a class='btn secondary' href='{_escape(secondary.href)}'>{_escape(secondary.label)}</a>
            </div>
        </header>
        <main>
            <section class='brand-panel'>
                <h2>Brand tokens</h2>
                <div class='token-grid'>
                    {_token_block("Primary color", site.brandTokens.primaryColor.value, site.brandTokens.primaryColor.evidence.inferenceLabel)}
                    {_token_block("Accent color", site.brandTokens.accentColor.value, site.brandTokens.accentColor.evidence.inferenceLabel)}
                    {_token_block("Typography", site.brandTokens.typography.value, site.brandTokens.typography.evidence.inferenceLabel)}
                    {_token_block("Visual tone", site.brandTokens.visualTone.value, site.brandTokens.visualTone.evidence.inferenceLabel)}
                </div>
            </section>
            {sections_html}
            <section class='source-notes'>
                <h2>Source traceability</h2>
                <div class='source-grid'>
                    {source_cards}
                </div>
            </section>
        </main>
        <footer class='footer-cta'>
            <a class='btn tertiary' href='{_escape(footer.href)}'>{_escape(footer.label)}</a>
        </footer>
    </body>
    </html>"""


def _export_css(site: GeneratedSite) -> str:
    palette = site.paletteMode
    surface, text, muted = _palette_tokens(palette)
    accent = site.brandTokens.accentColor.value or "#38bdf8"
    return f"""
    :root {{
        --surface: {surface};
        --text: {text};
        --muted: {muted};
        --accent: {accent};
    }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: var(--surface);
        color: var(--text);
        margin: 0;
        line-height: 1.5;
        padding: 0;
    }}
    .hero {{
        padding: 4rem clamp(1.5rem, 5vw, 6rem);
        background: var(--text);
        color: var(--surface);
    }}
    .hero .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.4em;
        font-size: 0.75rem;
        opacity: 0.7;
    }}
    .hero h1 {{
        font-size: clamp(2.5rem, 5vw, 4rem);
        margin: 1rem 0;
    }}
    .hero .supported {{
        max-width: 720px;
        font-size: 1.1rem;
        opacity: 0.9;
    }}
    main {{
        padding: clamp(1.5rem, 4vw, 4rem);
    }}
    .cta-row {{
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 2rem;
    }}
    .btn {{
        padding: 0.85rem 1.5rem;
        border-radius: 999px;
        font-size: 0.95rem;
        text-decoration: none;
        transition: opacity 0.2s ease;
    }}
    .btn.primary {{ background: var(--accent); color: var(--surface); }}
    .btn.secondary {{ border: 1px solid rgba(255,255,255,0.35); color: var(--surface); }}
    .btn.tertiary {{ border: 1px solid var(--text); color: var(--text); }}
    .btn:hover {{ opacity: 0.85; }}
    .site-section {{
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 32px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        background: white;
    }}
    .site-section h3 {{
        margin-top: 0.35rem;
        margin-bottom: 0.5rem;
        font-size: 1.5rem;
    }}
    .section-items {{
        list-style: none;
        padding: 0;
        margin: 1rem 0 0;
        display: grid;
        gap: 0.75rem;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}
    .section-items li {{
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 18px;
        padding: 0.75rem 1rem;
    }}
    .brand-panel {{
        border-radius: 32px;
        padding: 2rem;
        background: rgba(255,255,255,0.75);
        border: 1px solid rgba(0,0,0,0.05);
        margin-bottom: 2rem;
    }}
    .token-grid {{
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .token {{
        border-radius: 18px;
        border: 1px solid rgba(0,0,0,0.06);
        padding: 1rem;
    }}
    .token-label {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.18em; color: var(--muted); }}
    .token-value {{ font-size: 1.1rem; margin-top: 0.5rem; }}
    .token-note {{ font-size: 0.85rem; color: var(--muted); }}
    .source-notes {{
        margin-top: 2rem;
    }}
    .source-grid {{
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .source-card {{
        border-radius: 18px;
        border: 1px solid rgba(0,0,0,0.06);
        padding: 1rem;
        background: white;
    }}
    .source-kind {{ font-size: 0.75rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); }}
    .source-label {{ font-weight: 600; margin: 0.5rem 0; }}
    .source-url {{ font-size: 0.8rem; color: var(--muted); word-break: break-all; }}
    .footer-cta {{
        padding: 2rem clamp(1.5rem, 5vw, 6rem);
        display: flex;
        justify-content: center;
        border-top: 1px solid rgba(0,0,0,0.08);
    }}
    .muted {{ color: var(--muted); }}
    @media (prefers-color-scheme: dark) {{
        body {{ background: #020617; color: #f8fafc; }}
        .site-section, .brand-panel, .token, .source-card {{ background: rgba(2,6,23,0.7); border-color: rgba(255,255,255,0.08); }}
    }}
    """


def _section_html(section: Any) -> str:
    items = (
        "\n".join(
            f"<li>{_escape(item)}</li>"
            for item in getattr(section, "items", [])
            if item
        )
        or ""
    )
    items_block = f"<ul class='section-items'>{items}</ul>" if items else ""
    eyebrow = getattr(section, "eyebrow", None)
    return f"""
    <section class='site-section'>
        <p class='eyebrow'>{_escape(eyebrow)}</p>
        <h3>{_escape(section.headline or section.title)}</h3>
        <p>{_escape(section.body)}</p>
        {items_block}
        {_cta_block(section)}
    </section>
    """


def _cta_block(section: Any) -> str:
    label = getattr(section, "ctaLabel", None)
    if not label:
        return ""
    return f"<div class='muted'>{_escape(label)}</div>"


def _token_block(label: str, value: str, note: str) -> str:
    return f"""
    <div class='token'>
        <div class='token-label'>{_escape(label)}</div>
        <div class='token-value'>{_escape(value)}</div>
        <div class='token-note'>{_escape(note)}</div>
    </div>
    """


def _palette_tokens(mode: str) -> tuple[str, str, str]:
    if mode == "light":
        return ("#f8fafc", "#0f172a", "#475569")
    if mode == "colorful":
        return ("linear-gradient(135deg,#0f172a,#312e81)", "#e0e7ff", "#c7d2fe")
    return ("#020617", "#f8fafc", "#94a3b8")


def _escape(value: Any) -> str:
    return html.escape(_text(value))
