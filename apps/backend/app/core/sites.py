from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, cast
from uuid import uuid4

from pymongo.results import UpdateResult
from app.core.analytics import analytics_repository
from app.core.color_system import generate_color_system
from app.core.config import get_settings
from app.core.industry_detection import get_industry_design_config
from app.core.leads import _job_doc_to_summary, lead_repository  # type: ignore[attr-defined]
from app.core.mongo import get_database
from app.core.generation_run import brand_snapshot_hash, generation_input_hash, supersede_reason
from app.core.screenshot_comparator import ScreenshotComparator
from app.schemas.brief import (
    BriefEvidence,
    SiteBrief,
    VisualCritique,
    VisualRedesignBrief,
)
from app.schemas.extraction import ExtractionSnapshot
from app.schemas.lead import JobSummary
from app.schemas.site import (
    BrandTokens,
    CtaAction,
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
    SiteToken,
    ThemeLibraryResponse,
    ThemeVariant,
    VariantType,
)

logger = logging.getLogger(__name__)


CLIENT_VARIANT_COPY: dict[str, tuple[str, str]] = {
    "html_v1": ("The Authority Edit", "Editorial clarity with a composed, high-trust presentation."),
    "html_v2": ("Signal & Structure", "A confident, energetic direction built for momentum and action."),
    "html_v3": ("The Counsel Atelier", "A warmer, more distinctive expression with memorable detail."),
    "nextjs": ("The Interactive Brief", "A polished interactive direction with room for richer product moments."),
}


def is_usable_generated_site(site: GeneratedSite) -> bool:
    """Return true only when the persisted artifact can actually be previewed."""
    if site.readinessStatus == "blocked" or not (site.previewUrl or site.previewSlug):
        return False
    if site.variantType in {"html_v1", "html_v2", "html_v3"}:
        return bool(
            site.staticHtml
            and site.staticHtml.strip()
            and site.compilationStatus in {"success", "completed"}
        )
    return bool(
        site.compiledBundleUrl
        and site.compiledBundleUrl.strip()
        and site.compilationStatus in {"success", "completed"}
    )


def _client_variant_copy(
    variant_strategy: dict[str, Any], company_name: str | None = None
) -> tuple[str, str]:
    variant_type = str(variant_strategy.get("variantType") or "nextjs")
    default_title, default_description = CLIENT_VARIANT_COPY.get(
        variant_type, ("A New Direction", "A distinct visual direction shaped around the approved brief.")
    )
    title = str(variant_strategy.get("variantTitle") or default_title)
    if company_name and company_name.strip():
        title = f"{company_name.strip()} — {title}"
    return title, str(variant_strategy.get("variantDescription") or default_description)


async def _generate_client_variant_copy(
    *,
    master_brief: Any,
    variant_strategy: dict[str, Any],
    extraction: ExtractionSnapshot,
) -> tuple[str, str]:
    """Generate the client-facing variant name and description from the brief.

    Variant labels are internal strategy metadata. The preview card should have
    editorial copy that reflects the actual company, approved positioning, and
    the variant's creative direction, so it must not use a fixed global label.
    """
    from app.core.llm import get_llm_client

    company_name = _text(getattr(extraction.summary, "companyName", None)) or "the company"
    creative_direction = getattr(master_brief, "creativeDirection", None)
    direction = creative_direction.model_dump(mode="json") if creative_direction else {}
    prompt = f"""
Create the client-facing name and one-sentence description for one website design
direction. Use only the approved brief and design direction below.

Company: {company_name}
Approved brief:
- Value proposition: {_text(getattr(master_brief, "valueProposition", ""))}
- Audience: {_text(getattr(master_brief, "primaryAudience", ""))}
- Hero headline: {_text(getattr(master_brief, "headline", ""))}
- Supporting line: {_text(getattr(master_brief, "subheadline", ""))}
- Tone: {_text(getattr(master_brief, "toneAndVoice", ""))}

Design direction:
{json.dumps(direction, ensure_ascii=False)}

Variant strategy:
- Design mode: {_text(variant_strategy.get("designMode"))}
- Creative guidance: {_text(variant_strategy.get("creativeBriefGuidance"))}

Return JSON only with exactly these keys:
{{"title": "a distinctive 2-6 word design name", "description": "one concise 10-22 word sentence describing this design direction"}}

The title must be specific to this company's approved brief and this design
direction. Do not use generic fixed labels such as "The Authority Edit",
"Signal & Structure", or "The Counsel Atelier". Do not introduce claims,
services, locations, or industry terms that are absent from the brief. Do not
mention water or wells unless the approved brief explicitly does.
""".strip()

    try:
        llm = get_llm_client()
        response = await llm.generate_text(prompt=prompt, temperature=0.7, max_tokens=500)
        data = llm.extract_json_from_response(response)
        title = _text(data.get("title")).strip().strip('"')
        description = _text(data.get("description")).strip().strip('"')
        if title and description:
            return title[:120], description[:240]
        logger.warning("LLM returned incomplete client variant copy; using brief fallback")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Client variant copy generation failed: %s", exc)

    # This fallback is still brief-backed and company-scoped for providers that
    # are temporarily unavailable; normal production generation uses the LLM.
    fallback_title, fallback_description = _client_variant_copy(
        variant_strategy, company_name
    )
    return fallback_title, fallback_description

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

    logo_value = (
        (logo_cues[0]["cachedUri"] or logo_cues[0]["sourceUrl"])
        if logo_cues
        else "No logo asset captured"
    )
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
        (image_cues[0]["cachedUri"] or image_cues[0]["sourceUrl"])
        if image_cues
        else "No image direction captured"
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

    # Deterministic factual/runtime failures are never recoverable through a
    # visual fallback score. Callers pass these markers from generation and QA.
    fatal_markers = {
        "invalid_javascript", "runtime_initialization_failed", "missing_stylesheet",
        "missing_script", "wrong_mime_type", "broken_main_content",
        "required_interaction_failed", "fake_business_contact", "missing_valid_logo",
        "stale_footer_year", "diversity_gate_failed",
    }
    if any(any(marker in str(requirement).lower() for marker in fatal_markers) for requirement in missing_requirements):
        return 0

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

    # Fallback: data-richness score (no visual validation available)
    # Base reflects a minimally complete pipeline run
    score = 40

    # Brief quality (up to +20)
    if brief.approvalState == "approved":
        score += 8
    # MasterBrief stores the approved content blueprint as `sections`.
    # Keep this tolerant of older brief objects so persistence cannot fail
    # while calculating a fallback quality score.
    score += min(len(getattr(brief, "sections", []) or []), 5) * 2  # up to +10
    score += min(len(getattr(brief, "proofPoints", []) or []), 2) * 1  # up to +2

    # Brief confidence (0–100 → up to +8)
    score += int(brief.confidenceScore * 0.08)

    # Extraction richness (up to +15)
    score += min(len(extraction.sourceCitations), 5) * 1  # up to +5
    score += min(len(extraction.brandAssetCues), 3) * 1  # up to +3
    score += min(extraction.pagesCrawled, 5) * 1  # up to +5
    if extraction.extractedTestimonials:
        score += 1
    if extraction.extractedImages:
        score += 1

    # Extraction confidence (0–100 → up to +5)
    score += int(extraction.confidenceScore * 0.05)

    # Brand tokens grounded in source data (up to +6)
    if brand_tokens["primaryColor"]["evidence"]["sourceKind"] == "source_backed":
        score += 3
    if brand_tokens["typography"]["evidence"]["sourceKind"] == "source_backed":
        score += 3

    # Visual redesign briefs present (up to +4)
    score += min(len(getattr(brief, "visualRedesign", []) or []), 2) * 2

    # Diversity bonus (up to +3)
    score += int(diversity_score * 0.06)

    # Penalise missing requirements
    score -= min(len(missing_requirements), 5) * 4

    return max(0, min(100, score))


def _default_brand_tokens_dict() -> dict[str, Any]:
    """Return a minimal brand tokens dict for use when no extraction-derived tokens are available."""
    inferred = {
        "sourceKind": "inferred",
        "inferenceLabel": "Default",
        "confidence": 0,
        "references": [],
    }
    return {
        "paletteMode": "zinc",
        "primaryColor": {"value": "#3b82f6", "evidence": inferred},
        "secondaryColor": {"value": "#64748b", "evidence": inferred},
        "accentColor": {"value": "#f59e0b", "evidence": inferred},
        "backgroundColor": {"value": "#ffffff", "evidence": inferred},
        "textColor": {"value": "#1a1a2e", "evidence": inferred},
        "borderColor": {"value": "#e2e8f0", "evidence": inferred},
        "typography": {"value": "system-ui, sans-serif", "evidence": inferred},
        "imageStyle": {"value": "clean", "evidence": inferred},
        "visualTone": {"value": "modern", "evidence": inferred},
        "motionIntensity": {"value": "subtle", "evidence": inferred},
        "layoutDensity": {"value": "balanced", "evidence": inferred},
    }


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


def _migrate_evidence_source_kind(doc: dict[str, Any]) -> None:
    """Migrate legacy 'extraction' sourceKind values to 'source_backed'."""

    def fix_evidence(obj: Any) -> None:
        """Recursively fix sourceKind in all evidence fields."""
        if isinstance(obj, dict):
            if "sourceKind" in obj and obj["sourceKind"] == "extraction":
                obj["sourceKind"] = "source_backed"
            for value in obj.values():
                fix_evidence(value)
        elif isinstance(obj, list):
            for item in obj:
                fix_evidence(item)

    fix_evidence(doc)


def _site_doc_to_current(doc: dict[str, Any]) -> GeneratedSite:
    _migrate_evidence_source_kind(doc)
    return GeneratedSite.model_validate(doc)


def _site_version_doc_to_model(doc: dict[str, Any]) -> GeneratedSiteVersion:
    _migrate_evidence_source_kind(doc)
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
        variantType=site.variantType,
        paletteMode=site.paletteMode,
        qualityScore=site.qualityScore,
        readinessStatus=site.readinessStatus,
        qaStatus=site.qaStatus,
        publishApprovalState=site.publishApprovalState,
        reviewState=site.browserReviewState,
        missingRequirements=list(site.missingRequirements),
        reviewRubric=list(site.reviewRubric),
        screenshotCount=len(site.screenshotRefs),
        screenshotRefs=list(site.screenshotRefs),
        sourceAttribution=site.sourceAttribution,
        isManuallyRefined=site.isManuallyRefined,
        refinedCount=len([p for p in site.promptHistory if p.status == "completed"]),
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
        self._generation_runs: dict[str, dict[str, Any]] = {}

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None or self._memory_ready:
            return
        self._memory_ready = True
        await database["generated_sites"].create_index("id", unique=True)
        await database["generated_sites"].create_index("leadId")
        await database["generated_sites"].create_index("previewSlug")
        await database["generated_sites"].create_index("generationRunId")
        await database["generated_sites"].create_index([("generationRunId", 1), ("variantType", 1)], unique=True, partialFilterExpression={"generationRunId": {"$type": "string"}})
        await database["generation_runs"].create_index("id", unique=True)
        await database["generation_runs"].create_index([("leadId", 1), ("createdAt", -1)])
        await database["generation_runs"].create_index([("leadId", 1), ("status", 1)])
        await database["generation_runs"].create_index("generationInputHash")
        await database["generation_input_claims"].create_index([("leadId", 1), ("generationInputHash", 1)], unique=True)
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

    async def get_diversity_report(
        self, limit: int = 100, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Returns batch-level diversity metrics for the last N sites.
        """
        sites = await self._list_sites(limit=limit, offset=0, user_id=user_id)

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
            logger.info("Auto-iteration disabled: visual_redesign_enabled=False")
            return

        # Treat values <= 1 as "no automatic iteration".
        try:
            max_iterations = int(getattr(settings, "visual_redesign_max_iterations", 0))
        except Exception:
            max_iterations = 0
        if max_iterations <= 1:
            logger.info(
                "Auto-iteration disabled: max_iterations=%d (must be > 1)",
                max_iterations,
            )
            return

        try:
            # Load the latest generated site to inspect version and any
            # improvement recommendations produced during screenshot QA.
            site = await self.get_site(site_id)
            if site is None:
                logger.warning("Auto-iteration skipped: site %s not found", site_id)
                return

            try:
                job_doc = await lead_repository.get_job_doc(job_id)
            except Exception:
                job_doc = None

            metadata = (job_doc or {}).get("metadata", {}) or {}

            # Guard: verify the current generation actually persisted by
            # comparing the site version against the job's expected version.
            # Without this, a persistence failure would leave a stale version
            # and the iteration logic could loop indefinitely.
            expected_version = metadata.get("nextVersion")
            if expected_version is not None:
                current_version_actual = int(getattr(site, "version", 0))
                if current_version_actual < int(expected_version):
                    logger.warning(
                        "Auto-iteration skipped for %s: site version %d < expected %d "
                        "(generation may not have persisted)",
                        site_id,
                        current_version_actual,
                        int(expected_version),
                    )
                    return

            screenshot_qa = metadata.get("screenshotQA") or {}
            screenshot_quality = screenshot_qa.get("qualityScore")
            screenshot_success = screenshot_qa.get("success", False)

            # CRITICAL FIX: Only proceed if screenshot QA actually ran and has results
            # Without this, we would loop infinitely on every successful generation
            if not screenshot_qa:
                logger.info(
                    "Auto-iteration skipped for %s: No screenshot QA data in job metadata",
                    site_id,
                )
                return

            if not screenshot_success:
                logger.info(
                    "Auto-iteration skipped for %s: screenshot QA failed (success=%s)",
                    site_id,
                    screenshot_success,
                )
                return

            if screenshot_quality is None:
                logger.info(
                    "Auto-iteration skipped for %s: screenshot QA quality score is None",
                    site_id,
                )
                return

            threshold = int(getattr(settings, "visual_redesign_quality_threshold", 95))
            if int(screenshot_quality) >= threshold:
                logger.info(
                    "Auto-iteration skipped for %s: quality score %d >= threshold %d",
                    site_id,
                    screenshot_quality,
                    threshold,
                )
                return

            # Enforce a hard cap on how many generations we will run
            # automatically. Version numbers are 1-based, so with
            # max_iterations=2 we allow a single follow-up pass.
            current_version = int(getattr(site, "version", 0))
            if current_version >= max_iterations:
                logger.info(
                    "Auto-iteration skipped for %s: current version %d >= max_iterations %d",
                    site_id,
                    current_version,
                    max_iterations,
                )
                return

            if not getattr(site, "improvementRecommendations", None):
                logger.info(
                    "Auto-iteration skipped for %s: no improvement recommendations available",
                    site_id,
                )
                return

            logger.info(
                "Queuing automatic refinement generation for %s (version %s -> %s, quality score: %d)",
                site_id,
                current_version,
                current_version + 1,
                screenshot_quality,
            )

            force_flag = bool(getattr(request, "force", False)) if request else False
            # Carry forward any human-supplied refinement prompt so auto-iteration
            # doesn't discard operator instructions from the triggering request.
            carried_prompt_id = (
                getattr(request, "refinementPromptId", None) if request else None
            )
            auto_request = SiteGenerateRequest(
                force=force_flag, refinementPromptId=carried_prompt_id
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

    async def get_site(
        self, site_id: str, user_id: str | None = None
    ) -> GeneratedSite | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        query: dict[str, Any] = {"id": site_id}
        if user_id:
            query["userId"] = user_id
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if not doc:
                    # Fallback: treat site_id as a leadId and return lowest-position variant
                    candidates = [
                        d
                        for d in self._sites.values()
                        if d.get("leadId") == site_id
                        and (not user_id or d.get("userId") == user_id)
                    ]
                    if candidates:
                        doc = min(
                            candidates, key=lambda d: d.get("variantPosition", 99)
                        )
                if doc:
                    if user_id and doc.get("userId") != user_id:
                        return None
                    site = _site_doc_to_current(doc)
                    diffs = await self.get_override_diff(site.id)
                    site.overrideDiffs = diffs
                    return site
                return None
        doc = await database["generated_sites"].find_one(query)
        if not doc:
            # Fallback: treat site_id as a leadId and return lowest-position variant
            lead_query: dict[str, Any] = {"leadId": site_id}
            if user_id:
                lead_query["userId"] = user_id
            cursor = (
                database["generated_sites"]
                .find(lead_query)
                .sort("variantPosition", 1)
                .limit(1)
            )
            docs = await cursor.to_list(length=1)
            doc = docs[0] if docs else None
        if doc:
            site = _site_doc_to_current(doc)
            diffs = await self.get_override_diff(site.id)
            site.overrideDiffs = diffs
            return site
        return None

    async def delete_site(self, site_id: str, user_id: str | None = None) -> bool:
        await self._maybe_ensure_indexes()
        database = get_database()
        query: dict[str, Any] = {"id": site_id}
        if user_id:
            query["userId"] = user_id
        if database is None:
            async with self._memory_lock:
                if site_id in self._sites:
                    if user_id and self._sites[site_id].get("userId") != user_id:
                        return False
                    del self._sites[site_id]
                    return True
                return False
        result = await database["generated_sites"].delete_one(query)
        return result.deleted_count > 0

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

    async def list_sites_by_lead(
        self, lead_id: str, user_id: str | None = None
    ) -> list[GeneratedSite]:
        """Get all site variants for a lead."""
        await self._maybe_ensure_indexes()
        database = get_database()
        query: dict[str, Any] = {"leadId": lead_id}
        if user_id:
            query["userId"] = user_id
        if database is None:
            async with self._memory_lock:
                sites = [
                    _site_doc_to_current(doc)
                    for doc in self._sites.values()
                    if doc.get("leadId") == lead_id
                    and (not user_id or doc.get("userId") == user_id)
                ]
                return sorted(sites, key=lambda s: s.variantPosition)

        cursor = database["generated_sites"].find(query)
        docs = await cursor.to_list(length=100)
        sites = [_site_doc_to_current(doc) for doc in docs]
        return sorted(sites, key=lambda s: s.variantPosition)

    async def persist_visual_quality(
        self, site_id: str, quality_score: int, qa_metadata: dict[str, Any]
    ) -> None:
        """Replace the provisional score after visual QA and runtime checks."""
        score = max(0, min(100, int(quality_score)))
        runtime = qa_metadata.get("runtimeQA") or {}
        fatal_runtime = bool(runtime.get("fatalRuntimeFailures")) or runtime.get("runtimeStatus") == "failed"
        if fatal_runtime:
            # Vision availability or a prior fallback score can never mask a
            # parse/load/init failure in a public preview.
            score = 0
        if runtime:
            penalties = 0
            if runtime.get("consoleErrors") or runtime.get("pageErrors"):
                penalties += 20
            if runtime.get("failedRequests"):
                penalties += 15
            if runtime.get("brokenImages") or runtime.get("imageLoadTimeout"):
                penalties += 15
            if runtime.get("hiddenAfterScroll"):
                penalties += 15
            if runtime.get("horizontalOverflow"):
                penalties += 10
            if runtime.get("fontsReady") is False:
                penalties += 10
            score = max(0, score - penalties)
            qa_metadata = {
                **qa_metadata,
                "qualityComponents": {
                    "brandFidelity": int(qa_metadata.get("brandFidelity", score)),
                    "visualImpact": int(qa_metadata.get("visualImpact", score)),
                    "typography": int(qa_metadata.get("typography", score)),
                    "layoutComposition": int(qa_metadata.get("layoutComposition", score)),
                    "imagery": int(qa_metadata.get("imagery", score)),
                    "responsiveness": 0 if runtime.get("horizontalOverflow") else 100,
                    "runtimeHealth": 0 if penalties else 100,
                    "contentCompleteness": 0 if runtime.get("hiddenAfterScroll") else 100,
                },
                "runtimePenalty": penalties,
            }
        now = _now()
        update = {
            "qualityScore": score,
            "qualityScoreSource": "visual",
            "screenshotQA": qa_metadata,
            "updatedAt": now,
        }
        if fatal_runtime:
            update.update({"qaStatus": "fail", "readinessStatus": "blocked"})
        database = get_database()
        if database is None:
            async with self._memory_lock:
                if site_id in self._sites:
                    self._sites[site_id].update(update)
            return
        await database["generated_sites"].update_one({"id": site_id}, {"$set": update})

    async def generate_site_variant(
        self,
        *,
        lead_id: str,
        variant_type: VariantType,
        variant_strategy: dict[str, Any],
        extraction: ExtractionSnapshot,
        analysis: Any,
        user_id: str,
        approved_brief: Any | None = None,
        generation_run_id: str | None = None,
    ) -> GeneratedSite:
        """
        Generate a single site variant (HTML or Next.js).

        Args:
            lead_id: Lead identifier
            variant_type: Type of variant to generate
            variant_strategy: Strategy definition from variant_strategy.py
            extraction: Extraction snapshot (shared across variants)
            analysis: Analysis results (shared across variants)
            user_id: User ID for audit trail

        Returns:
            Generated site variant
        """
        from app.core.master_brief import generate_master_brief
        from app.core.static_html_generator import generate_static_html
        from app.core.ai_site_generation import generate_landing_page_code

        if generation_run_id:
            database = get_database()
            existing_doc = None
            if database is not None:
                existing_doc = await database["generated_sites"].find_one({"generationRunId": generation_run_id, "variantType": variant_type})
            else:
                async with self._memory_lock:
                    existing_doc = next((d for d in self._sites.values() if d.get("generationRunId") == generation_run_id and d.get("variantType") == variant_type), None)
            if existing_doc:
                return GeneratedSite.model_validate(existing_doc)

        # Step 1: derive a variant brief from the approved brief. This preserves
        # the exact approved brand assets and factual source while allowing each
        # variant to have an independent creative direction.
        industry = None
        if analysis and hasattr(analysis, "analysis"):
            industry = getattr(analysis.analysis, "industry", None)

        if approved_brief is None:
            logger.info(f"Generating master brief for {variant_type} (legacy path)")
            master_brief = await generate_master_brief(lead_id=lead_id, extraction=extraction, variant_type=variant_type, industry=industry)
        else:
            # Keep hero copy source-backed. Variant diversity comes from the
            # strategy and art direction, never from industry-specific copy
            # accidentally applied to an unrelated lead.
            variant_copy = (
                approved_brief.headline,
                approved_brief.subheadline,
                approved_brief.ctaStrategy,
            )
            ordered_sections = list(approved_brief.sections)
            if variant_type == "html_v2":
                ordered_sections = sorted(ordered_sections, key=lambda section: 0 if section.purpose in {"services", "process"} else 1)
            elif variant_type == "html_v3":
                ordered_sections = sorted(ordered_sections, key=lambda section: 0 if section.purpose in {"about", "proof", "testimonial"} else 1)
            master_brief = approved_brief.model_copy(deep=True, update={
                "id": f"{generation_run_id}:{variant_type}" if generation_run_id else approved_brief.id,
                "visualStyle": variant_strategy.get("designMode", approved_brief.visualStyle),
                "designMode": variant_strategy.get("designMode", approved_brief.designMode),
                "headline": variant_copy[0], "subheadline": variant_copy[1], "ctaStrategy": variant_copy[2], "sections": ordered_sections,
                "creativeDirection": approved_brief.creativeDirection.model_copy(update={
                    "designConcept": variant_strategy.get("creativeBriefGuidance", approved_brief.creativeDirection.designConcept),
                    "heroTreatment": {"html_v1": "Editorial authority with a source-backed hero image", "html_v2": "Cinematic service hero with an operational carousel", "html_v3": "Warm layered storytelling with a source-backed image collage"}.get(str(variant_type), approved_brief.creativeDirection.heroTreatment),
                    "signatureTechnique": {"html_v1": "Measured editorial reveal", "html_v2": "Service carousel with controls", "html_v3": "Layered storytelling scroll"}.get(str(variant_type), approved_brief.creativeDirection.signatureTechnique),
                    "layoutStrategy": {"html_v1": "Asymmetric editorial columns", "html_v2": "Full-bleed cinematic panels", "html_v3": "Warm staggered storytelling blocks"}.get(str(variant_type), approved_brief.creativeDirection.layoutStrategy),
                    "colorMood": {"html_v1": "Bright, grounded brand neutrals", "html_v2": "Deep contrast with a focused brand accent", "html_v3": "Warm, tactile brand colors"}.get(str(variant_type), approved_brief.creativeDirection.colorMood),
                    "typographyPersonality": {"html_v1": "Authority-led editorial display", "html_v2": "Condensed technical display and humanist body", "html_v3": "Warm expressive display and clear body"}.get(str(variant_type), approved_brief.creativeDirection.typographyPersonality),
                    "inspirationKeywords": variant_strategy.get("inspirationKeywords", approved_brief.creativeDirection.inspirationKeywords),
                    "avoidPatterns": variant_strategy.get("avoidPatterns", approved_brief.creativeDirection.avoidPatterns),
                }),
            })

        # Save brief to database
        database = get_database()
        if database is not None:
            await database["master_briefs"].insert_one(
                master_brief.model_dump(by_alias=True)
            )

        # Step 2: Generate site based on variant type
        site_id = str(uuid4())
        slug = self._generate_variant_slug(
            lead_id, variant_type, extraction.summary.companyName
        )

        # Get existing slugs to avoid duplicates
        existing_slugs = await self._get_existing_slugs()

        # Ensure slug is unique
        base_slug = slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug[:6]}{counter}"
            counter += 1

        if variant_type == "nextjs":
            # Use existing Next.js generation
            logger.info(f"Generating Next.js site for {variant_type} (site {site_id})")
            try:
                code_result = await generate_landing_page_code(
                    master_brief=master_brief,
                    extraction=extraction,
                    site_id=site_id,
                )
            except Exception as e:
                logger.error(f"Next.js generation failed: {e}")
                code_result = {}

            site = await self._build_nextjs_site(
                site_id=site_id,
                lead_id=lead_id,
                master_brief=master_brief,
                variant_strategy=variant_strategy,
                slug=slug,
                code_result=code_result,
                extraction=extraction,
            )
        else:
            # Generate static HTML
            logger.info(f"Generating static HTML for {variant_type} (site {site_id})")
            # A failed generator call must abort before a GeneratedSite is
            # built or persisted. The caller records the structured failure.
            html_result = await generate_static_html(
                master_brief=master_brief,
                extraction=extraction,
                variant_type=variant_type,
                site_id=site_id,
            )
            if not html_result.get("html", "").strip():
                raise ValueError("static_html_empty_after_generation")

            site = await self._build_static_html_site(
                site_id=site_id,
                lead_id=lead_id,
                master_brief=master_brief,
                variant_strategy=variant_strategy,
                slug=slug,
                html_result=html_result,
                extraction=extraction,
            )

        # Stamp the owning user and source attribution before saving
        site.userId = user_id
        if generation_run_id:
            site.generationRunId = generation_run_id
            site.briefId = approved_brief.id if approved_brief else master_brief.id
            site.briefVersion = approved_brief.version if approved_brief else master_brief.version
            site.variantBriefId = master_brief.id
            site.variantBriefVersion = master_brief.version
            run = await self._get_generation_run(generation_run_id)
            if run:
                site.generationInputHash = run.get("generationInputHash")
                site.brandSnapshotHash = run["snapshot"].get("brandSnapshotHash")
                site.brandRevision = run["snapshot"].get("brandRevision", 1)
                site.extractionId = run["snapshot"].get("extractionId")
                site.extractionVersion = run["snapshot"].get("extractionVersion")
                site.generatorVersion = run["snapshot"].get("generatorVersion")
                site.promptVersion = run["snapshot"].get("promptVersion")
                await self._update_generation_run(generation_run_id, {"variantBriefs": [*(run.get("variantBriefs") or []), {"id": master_brief.id, "variantType": variant_type, "version": master_brief.version, "contentStrategy": {"headline": master_brief.headline, "sections": [s.purpose for s in master_brief.sections], "cta": master_brief.ctaStrategy}, "creativeStrategy": variant_strategy}]})
                previous = list(run.get("variantBriefs") or [])
                current_sections = [section.purpose for section in master_brief.sections]
                similarities: list[float] = []
                for item in previous:
                    content = item.get("contentStrategy") or {}
                    prior_sections = content.get("sections") or []
                    section_similarity = 1.0 if prior_sections == current_sections else len(set(prior_sections) & set(current_sections)) / max(1, len(set(prior_sections) | set(current_sections)))
                    headline_similarity = 1.0 if str(content.get("headline", "")).strip().lower() == master_brief.headline.strip().lower() else 0.0
                    similarities.append((section_similarity * 0.7) + (headline_similarity * 0.3))
                max_similarity = max(similarities, default=0.0)
                site.diversityScore = max(0, round((1 - max_similarity) * 100))
                site.diversityNotes = [f"Compared with {len(previous)} prior variants; maximum structural/content similarity {max_similarity:.2f}."]
                if max_similarity >= 0.95:
                    raise ValueError("diversity_gate_failed: identical section/copy blueprint")
        site.sourceAttribution = SiteSourceAttribution.model_validate(
            _site_source_attribution(
                lead=await lead_repository.get_lead(lead_id),
                brief=master_brief,
                extraction=extraction,
                theme={"themeKey": site.themeKey},
                palette_mode=site.paletteMode,
            )
        )

        # Save site to database
        if database is not None:
            await database["generated_sites"].insert_one(site.model_dump(by_alias=True))
        else:
            async with self._memory_lock:
                self._sites[site.id] = site.model_dump(by_alias=True)

        logger.info(f"Variant {variant_type} generated: {site.previewUrl}")

        return site

    def _generate_variant_slug(
        self,
        lead_id: str,
        variant_type: VariantType,
        company_name: str | None,
    ) -> str:
        """Generate preview slug for variant."""
        # Base slug from company name or lead ID
        if company_name:
            base = company_name.lower().replace(" ", "-").replace("_", "-")
            base = "".join(c for c in base if c.isalnum() or c == "-")
            base = base[:8]  # Truncate to 8 chars
        else:
            base = lead_id[:8]

        # Add variant suffix
        if variant_type == "html_v1":
            return f"{base}-v1"
        elif variant_type == "html_v2":
            return f"{base}-v2"
        elif variant_type == "html_v3":
            return f"{base}-v3"
        else:  # nextjs
            return base

    async def _get_existing_slugs(self) -> set[str]:
        """Get all existing preview slugs."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return {doc.get("previewSlug", "") for doc in self._sites.values()}

        cursor = database["generated_sites"].find({}, {"previewSlug": 1})
        docs = await cursor.to_list(length=10000)
        return {doc.get("previewSlug", "") for doc in docs}

    async def _build_nextjs_site(
        self,
        *,
        site_id: str,
        lead_id: str,
        master_brief: Any,
        variant_strategy: dict[str, Any],
        slug: str,
        code_result: dict[str, Any],
        extraction: ExtractionSnapshot,
    ) -> GeneratedSite:
        """Build GeneratedSite for Next.js variant."""
        settings = get_settings()
        preview_base = settings.preview_base_url.rstrip("/")

        sections = self._master_section_stack(master_brief, extraction)
        cta_strategy = self._master_cta_strategy(master_brief)
        variant_title, variant_description = await _generate_client_variant_copy(
            master_brief=master_brief,
            variant_strategy=variant_strategy,
            extraction=extraction,
        )
        return GeneratedSite(
            id=site_id,
            leadId=lead_id,
            briefId=master_brief.id,
            briefVersion=master_brief.version,
            version=1,
            variantType="nextjs",
            variantLabel=variant_strategy.get("variantLabel", "Next.js Site"),
            variantTitle=variant_title,
            variantDescription=variant_description,
            variantPosition=variant_strategy.get("variantPosition", 4),
            themeId="nextjs-generated",
            themeKey="nextjs-generated",
            themeName="Next.js Generated",
            themeRationale="AI-generated Next.js site",
            paletteMode=variant_strategy.get("paletteMode", "zinc"),
            paletteRationale="From variant strategy",
            brandTokens=self._brand_tokens_from_brief(master_brief),
            heroVariant=self._default_hero_variant(),
            sectionStack=[SiteSection.model_validate(section) for section in sections],
            ctaStrategy=CtaStrategy.model_validate(cta_strategy),
            qualityScore=_quality_score(
                brief=master_brief,
                extraction=extraction,
                brand_tokens=self._brand_tokens_from_brief(master_brief).model_dump(),
                site_sections=sections,
                missing_requirements=list(master_brief.missingRequirements or []),
            ),
            qualityScoreSource="fallback",
            readinessStatus="ready_for_review",
            qaStatus="warn",
            previewSlug=slug,
            previewUrl=f"{preview_base}/{slug}",
            overrideCount=0,
            sourceCode=code_result.get("sourceCode"),
            compiledBundleUrl=code_result.get("compiledBundleUrl"),
            compiledCssUrl=code_result.get("compiledCssUrl"),
            compilationStatus=code_result.get("compilationStatus", "pending"),
            createdAt=_now(),
            updatedAt=_now(),
        )

    async def _build_static_html_site(
        self,
        *,
        site_id: str,
        lead_id: str,
        master_brief: Any,
        variant_strategy: dict[str, Any],
        slug: str,
        html_result: dict[str, Any],
        extraction: ExtractionSnapshot,
    ) -> GeneratedSite:
        """Build GeneratedSite for static HTML variant."""
        settings = get_settings()
        preview_base = settings.preview_base_url.rstrip("/")

        sections = self._master_section_stack(master_brief, extraction)
        cta_strategy = self._master_cta_strategy(master_brief)
        variant_title, variant_description = await _generate_client_variant_copy(
            master_brief=master_brief,
            variant_strategy=variant_strategy,
            extraction=extraction,
        )
        return GeneratedSite(
            id=site_id,
            leadId=lead_id,
            briefId=master_brief.id,
            briefVersion=master_brief.version,
            version=1,
            variantType=variant_strategy.get("variantType", "html_v1"),
            variantLabel=variant_strategy.get("variantLabel", "Static HTML"),
            variantTitle=variant_title,
            variantDescription=variant_description,
            variantPosition=variant_strategy.get("variantPosition", 1),
            staticHtml=html_result.get("html"),
            staticCssUrl=html_result.get("cssUrl"),
            staticJsUrl=html_result.get("jsUrl"),
            themeId="static-html",
            themeKey="static-html",
            themeName="Static HTML",
            themeRationale="AI-generated static HTML",
            paletteMode=variant_strategy.get("paletteMode", "light"),
            paletteRationale="From variant strategy",
            brandTokens=self._brand_tokens_from_brief(master_brief),
            heroVariant=self._default_hero_variant(),
            sectionStack=[SiteSection.model_validate(section) for section in sections],
            ctaStrategy=CtaStrategy.model_validate(cta_strategy),
            qualityScore=_quality_score(
                brief=master_brief,
                extraction=extraction,
                brand_tokens=self._brand_tokens_from_brief(master_brief).model_dump(),
                site_sections=sections,
                missing_requirements=list(master_brief.missingRequirements or []),
            ),
            qualityScoreSource="fallback",
            readinessStatus="ready_for_review",
            qaStatus="warn",
            previewSlug=slug,
            previewUrl=f"{preview_base}/{slug}",
            overrideCount=0,
            sourceCode=html_result.get("html"),
            compilationStatus="success" if html_result.get("html") else "failed",
            createdAt=_now(),
            updatedAt=_now(),
        )

    def _brand_tokens_from_brief(self, brief: Any) -> BrandTokens:
        """Persist approved brief assets instead of unrelated defaults."""
        tokens = self._default_brand_tokens()
        assets = getattr(brief, "brandAssets", None)
        evidence = BriefEvidence(
            sourceKind="source_backed",
            inferenceLabel="Approved master brief",
            confidence=85,
        )
        if assets:
            values = {
                "primaryColor": assets.primaryColor,
                "secondaryColor": assets.secondaryColor,
                "accentColor": assets.palette.get("accent") or assets.secondaryColor or assets.primaryColor,
                "typography": assets.fontFamily,
            }
            for field, value in values.items():
                if value:
                    setattr(tokens, field, SiteToken(value=str(value), evidence=evidence))
            if assets.logoUrl:
                tokens.logoAsset = SiteToken(value=assets.logoUrl, evidence=evidence)
        return tokens

    def _master_section_stack(self, brief: Any, extraction: ExtractionSnapshot) -> list[dict[str, Any]]:
        """Convert the approved master brief blueprint into persisted site metadata."""
        evidence = BriefEvidence(sourceKind="source_backed", inferenceLabel="Approved master brief section", confidence=85)
        result: list[dict[str, Any]] = []
        for section in list(getattr(brief, "sections", []) or []):
            purpose = _text(section.purpose) or "section"
            result.append({
                "kind": purpose,
                "title": section.headline or purpose,
                "headline": section.headline or purpose,
                "body": _sanitize_public_copy(section.contentSummary),
                "items": [_sanitize_public_copy(item) for item in section.contentPoints[:6]],
                "ctaLabel": _ensure_client_safe_cta(_text(brief.conversionAction)) if purpose.lower() in {"cta", "contact", "conversion"} else None,
                "componentId": _map_section_kind_to_component_id(purpose),
                "evidence": evidence.model_dump(),
            })
        if not result:
            result.append({"kind": "overview", "title": "Overview", "headline": brief.headline,
                           "body": _sanitize_public_copy(brief.valueProposition), "items": [], "ctaLabel": None,
                           "componentId": _map_section_kind_to_component_id("overview"), "evidence": evidence.model_dump()})
        return result

    def _master_cta_strategy(self, brief: Any) -> dict[str, Any]:
        """Persist CTA labels and destinations derived from the approved conversion action."""
        action = _ensure_client_safe_cta(_text(getattr(brief, "conversionAction", "")) or "Get started")
        rationale = _text(getattr(brief, "ctaStrategy", "")) or _text(getattr(brief, "conversionAction", ""))
        evidence = BriefEvidence(sourceKind="source_backed", inferenceLabel="Approved conversion action", confidence=85).model_dump()
        return {"primary": {"label": action, "href": "#contact", "rationale": rationale, "evidence": evidence},
                "secondary": {"label": "Learn more", "href": "#overview", "rationale": "Lower-friction exploration path.", "evidence": evidence},
                "footer": {"label": action, "href": "#contact", "rationale": rationale, "evidence": evidence}}
    def _default_brand_tokens(self) -> BrandTokens:
        """Return default brand tokens."""
        default_evidence = BriefEvidence(
            sourceKind="inferred",
            inferenceLabel="Default value",
            confidence=50,
        )
        return BrandTokens(
            paletteMode="zinc",
            primaryColor=SiteToken(value="#3b82f6", evidence=default_evidence),
            secondaryColor=SiteToken(value="#64748b", evidence=default_evidence),
            accentColor=SiteToken(value="#f97316", evidence=default_evidence),
            backgroundColor=SiteToken(value="#0f172a", evidence=default_evidence),
            textColor=SiteToken(value="#f8fafc", evidence=default_evidence),
            borderColor=SiteToken(value="#1e293b", evidence=default_evidence),
            logoAsset=None,
            typography=SiteToken(
                value="system-ui, sans-serif", evidence=default_evidence
            ),
            imageStyle=SiteToken(value="modern", evidence=default_evidence),
            visualTone=SiteToken(value="professional", evidence=default_evidence),
            motionIntensity=SiteToken(value="subtle", evidence=default_evidence),
            layoutDensity=SiteToken(value="balanced", evidence=default_evidence),
        )

    def _default_hero_variant(self) -> HeroVariant:
        """Return default hero variant."""
        default_evidence = BriefEvidence(
            sourceKind="inferred",
            inferenceLabel="Default hero content",
            confidence=40,
        )
        return HeroVariant(
            headline="Welcome",
            subheadline="Discover what we offer",
            supportingLine="Professional services for your needs",
            primaryCta="Get Started",
            secondaryCta="Learn More",
            layout="centered",
            visualTreatment="clean",
            evidence=default_evidence,
        )

    def _default_cta_strategy(self) -> CtaStrategy:
        """Return default CTA strategy."""
        default_evidence = BriefEvidence(
            sourceKind="inferred",
            inferenceLabel="Default CTA",
            confidence=50,
        )
        return CtaStrategy(
            primary=CtaAction(
                label="Get Started",
                href="#contact",
                rationale="Primary conversion action",
                evidence=default_evidence,
            ),
            secondary=CtaAction(
                label="Learn More",
                href="#about",
                rationale="Secondary exploration action",
                evidence=default_evidence,
            ),
            footer=CtaAction(
                label="Contact Us",
                href="#contact",
                rationale="Footer contact action",
                evidence=default_evidence,
            ),
        )

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
        self, *, limit: int = 25, offset: int = 0, user_id: str | None = None
    ) -> SiteReviewQueueResponse:
        await self._maybe_ensure_indexes()
        sites = await self._list_sites(limit=limit, offset=offset, user_id=user_id)
        sites = await self._backfill_source_attribution(sites)
        items = [_queue_item_from_site(site) for site in sites]
        total = await self._count_sites(user_id=user_id)

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
        brief_for_attribution = master_brief

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
                    doc["readinessStatus"] = "published"
                    doc["publishedAt"] = now
                    doc["updatedAt"] = now
            await lead_repository._set_pipeline_stage(site_id, "published")  # noqa: SLF001
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
                    "browserReviewState": (
                        _review_state_from(site, review)
                        if record.get("reviewRecordId")
                        else site.browserReviewState or "not_reviewed"
                    ),
                    "readinessStatus": "published",
                    "publishedAt": now,
                    "updatedAt": now,
                }
            },
        )
        await lead_repository._set_pipeline_stage(site_id, "published")  # noqa: SLF001
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

    async def get_override_diff(self, site_id: str) -> list[dict[str, Any]]:
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
            database = get_database()
            if database is not None:
                site = await database["generated_sites"].find_one({"id": site_id})
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

    async def _get_generation_run(self, run_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return self._generation_runs.get(run_id)
        return await database["generation_runs"].find_one({"id": run_id})

    async def _save_generation_run(self, run: dict[str, Any]) -> None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._generation_runs[run["id"]] = run
            return
        await database["generation_runs"].insert_one(run)

    async def _update_generation_run(self, run_id: str, update: dict[str, Any]) -> None:
        update["updatedAt"] = _now()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                if run_id in self._generation_runs:
                    self._generation_runs[run_id].update(update)
            return
        await database["generation_runs"].update_one({"id": run_id}, {"$set": update})

    async def _claim_generation_input(self, *, lead_id: str, input_hash: str, job_id: str) -> dict[str, Any] | None:
        """Atomically claim an active immutable input fingerprint."""
        now = _now()
        claim = {"leadId": lead_id, "generationInputHash": input_hash, "jobId": job_id, "createdAt": now}
        database = get_database()
        if database is None:
            async with lead_repository._memory_lock:
                key = (lead_id, input_hash)
                claims = getattr(self, "_generation_input_claims", {})
                existing = claims.get(key)
                if existing:
                    return existing
                claims[key] = claim
                self._generation_input_claims = claims
                return None
        try:
            await database["generation_input_claims"].insert_one(claim)
            return None
        except Exception as exc:
            if "duplicate" not in str(exc).lower() and "11000" not in str(exc):
                raise
            return await database["generation_input_claims"].find_one({"leadId": lead_id, "generationInputHash": input_hash})

    async def _release_generation_input(self, *, lead_id: str, input_hash: str, job_id: str) -> None:
        database = get_database()
        if database is None:
            async with lead_repository._memory_lock:
                claims = getattr(self, "_generation_input_claims", {})
                claim = claims.get((lead_id, input_hash))
                if claim and claim.get("jobId") == job_id:
                    claims.pop((lead_id, input_hash), None)
            return
        await database["generation_input_claims"].delete_one({"leadId": lead_id, "generationInputHash": input_hash, "jobId": job_id})

    async def list_generation_runs(self, lead_id: str, limit: int = 20) -> list[dict[str, Any]]:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                runs = [r for r in self._generation_runs.values() if r.get("leadId") == lead_id]
                return sorted(runs, key=lambda r: r.get("createdAt", _now()), reverse=True)[:limit]
        cursor = database["generation_runs"].find({"leadId": lead_id}).sort("createdAt", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def _create_generation_run(
        self, *, lead: Any, extraction: ExtractionSnapshot, brief: Any,
        request: SiteGenerateRequest | None, job_id: str, requested_by: str | None = None,
    ) -> dict[str, Any]:
        generation_types = list((request.variantTypes if request and request.variantTypes else ["nextjs"]))
        assets = brief.brandAssets.model_dump(mode="json") if getattr(brief, "brandAssets", None) else {}
        instructions = None
        if request and request.refinementPromptId:
            instructions = f"refinement_prompt:{request.refinementPromptId}"
        from app.core.variant_strategy import get_variant_strategies
        all_strategies = get_variant_strategies(lead.industry)
        default_nextjs = {"variantType": "nextjs", "variantLabel": "Next.js Site", "variantPosition": 4,
                          "designMode": "interactive", "paletteMode": "zinc", "creativeBriefGuidance": "",
                          "inspirationKeywords": [], "avoidPatterns": []}
        strategies = [dict(all_strategies.get(v, default_nextjs if v == "nextjs" else {})) for v in generation_types]
        snapshot = {
            "leadId": lead.id, "leadVersion": getattr(lead, "version", None),
            "extractionId": extraction.id, "extractionVersion": extraction.version,
            "analysisId": extraction.id, "analysisVersion": extraction.version,
            "briefId": brief.id, "briefVersion": brief.version,
            "brandRevision": int(getattr(brief, "brandRevision", 1) or 1),
            "brandSnapshotHash": brand_snapshot_hash(assets), "brandSnapshot": assets,
            "approvedImageInventory": list(assets.get("imageInventory") or []),
            "rejectedImages": list(assets.get("rejectedImages") or []),
            "operatorInstructions": instructions, "generationTypes": generation_types,
            "variantStrategies": strategies, "generatorVersion": "generation-run-v1",
            "promptVersion": "master-brief-v1",
        }
        input_hash = generation_input_hash(snapshot)
        now = _now()
        run = {
            "id": uuid4().hex, "leadId": lead.id, "jobId": job_id, "status": "queued",
            "snapshot": snapshot, "generationInputHash": input_hash,
            "requestedBy": requested_by, "operatorInstructions": instructions,
            "variantBriefs": [], "variantResults": [], "createdAt": now,
            "startedAt": None, "finishedAt": None, "supersededByRunId": None,
            "supersededReason": None,
        }
        await self._save_generation_run(run)
        return run

    async def queue_generation_job(
        self, site_id: str, request: SiteGenerateRequest | None = None
    ) -> JobSummary | None:
        await self._maybe_ensure_indexes()
        lead = await lead_repository.get_lead(site_id)
        if lead is None:
            return None

        # Check for approved master brief (AI-native generation)
        master_brief = await lead_repository.get_master_brief(site_id)
        if master_brief is None or master_brief.approvalState != "approved":
            raise ValueError("brief_not_approved")

        extraction = await lead_repository.get_extraction(site_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("extraction_required")
        database = get_database()

        # Use source evidence when an imported lead did not carry an industry;
        # this prevents trade businesses from falling into SaaS defaults.
        if not getattr(lead, "industry", None):
            from app.core.industry_detection import detect_industry
            inferred_industry, confidence = detect_industry(
                company_name=extraction.summary.companyName or "",
                services=list(getattr(extraction.analysis, "services", []) or extraction.summary.serviceClues),
                content_snippets=[extraction.summary.positioningSummary or "", *extraction.summary.serviceClues],
            )
            lead.industry = inferred_industry
            if database is not None:
                await database["leads"].update_one({"id": lead.id, "industry": {"$in": [None, ""]}}, {"$set": {"industry": inferred_industry, "inferredIndustry": {"value": inferred_industry, "confidence": confidence, "extractionId": extraction.id, "source": "extraction"}, "updatedAt": _now()}})

        # Build a pinned run before deduplicating. Active jobs only match when the
        # immutable input fingerprint is identical; a lead-only guard caused stale reuse.
        requested_by = getattr(lead, "user_id", None)
        assets_for_hash = master_brief.brandAssets.model_dump(mode="json")
        prospective = {"leadId": lead.id, "leadVersion": getattr(lead, "version", None),
                       "briefId": master_brief.id, "briefVersion": master_brief.version,
                       "extractionId": extraction.id, "extractionVersion": extraction.version,
                       "analysisId": extraction.id, "analysisVersion": extraction.version,
                       "generationTypes": list(request.variantTypes if request and request.variantTypes else ["nextjs"]),
                       "operatorInstructions": f"refinement_prompt:{request.refinementPromptId}" if request and request.refinementPromptId else None,
                       "brandSnapshotHash": brand_snapshot_hash(assets_for_hash), "brandSnapshot": assets_for_hash,
                       "approvedImageInventory": list(assets_for_hash.get("imageInventory") or []), "rejectedImages": list(assets_for_hash.get("rejectedImages") or []),
                       "brandRevision": int(getattr(master_brief, "brandRevision", 1) or 1),
                       "variantStrategies": [],
                       "generatorVersion": "generation-run-v1", "promptVersion": "master-brief-v1"}
        from app.core.variant_strategy import get_variant_strategies
        default_nextjs = {"variantType": "nextjs", "variantLabel": "Next.js Site", "variantPosition": 4,
                          "designMode": "interactive", "paletteMode": "zinc", "creativeBriefGuidance": "",
                          "inspirationKeywords": [], "avoidPatterns": []}
        strategy_map = get_variant_strategies(lead.industry)
        prospective["variantStrategies"] = [dict(strategy_map.get(v, default_nextjs if v == "nextjs" else {})) for v in prospective["generationTypes"]]
        input_hash = generation_input_hash(prospective)
        # This claim closes the read-then-create race between identical requests.
        # It is released only after runtime QA has finalized the run.
        provisional_job_id = uuid4().hex
        existing_claim = await self._claim_generation_input(lead_id=site_id, input_hash=input_hash, job_id=provisional_job_id)
        if existing_claim is not None:
            existing_job_id = existing_claim.get("jobId")
            existing_job = await database["jobs"].find_one({"id": existing_job_id}) if database is not None else lead_repository._jobs.get(existing_job_id)
            if existing_job is not None:
                await self._release_generation_input(lead_id=site_id, input_hash=input_hash, job_id=provisional_job_id)
                return _job_doc_to_summary(existing_job)
            await self._release_generation_input(lead_id=site_id, input_hash=input_hash, job_id=existing_job_id or "")
            existing_claim = await self._claim_generation_input(lead_id=site_id, input_hash=input_hash, job_id=provisional_job_id)
            if existing_claim is not None:
                raise ValueError("generation_input_claim_unavailable")
        if database is not None:
            existing_gen_job = await database["jobs"].find_one({"leadId": site_id, "jobType": {"$in": ["site_generate", "site_republish"]}, "status": {"$in": ["queued", "running"]}, "metadata.generationInputHash": input_hash})
            if existing_gen_job is not None:
                logger.info(
                    "Generation already in progress for site %s (job %s)",
                    site_id,
                    existing_gen_job["id"],
                )
                await self._release_generation_input(lead_id=site_id, input_hash=input_hash, job_id=provisional_job_id)
                return _job_doc_to_summary(existing_gen_job)
        else:
            async with lead_repository._memory_lock:
                existing_gen_job = next((j for j in lead_repository._jobs.values()
                    if site_id in j.get("leadIds", []) and j.get("jobType") in {"site_generate", "site_republish"}
                    and j.get("status") in {"queued", "running"}
                    and (j.get("metadata") or {}).get("generationInputHash") == input_hash), None)
                if existing_gen_job is not None:
                    return _job_doc_to_summary(existing_gen_job)

        current = await self.get_site(site_id)
        next_version = int(current.version if current else 0) + 1
        job_type = "site_generate" if current is None else "site_republish"

        # Master brief path skips diversity checks as AI generation handles variety naturally
        if not request or not request.force:
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
                    _text(master_brief.valueProposition),
                    _text(master_brief.primaryAudience),
                    _text(master_brief.toneAndVoice),
                    _text(master_brief.conversionAction),
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
                        _text(master_brief.toneAndVoice),
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
                "briefId": master_brief.id if master_brief else "",
                "briefVersion": master_brief.version if master_brief else 0,
                "nextVersion": next_version,
                "request": request.model_dump() if request else {},
            },
            job_id=provisional_job_id,
        )
        run = await self._create_generation_run(lead=lead, extraction=extraction, brief=master_brief, request=request, job_id=job.id, requested_by=requested_by)
        # Pin the run before dispatch so runtime QA can advance the lead only
        # when this is still the latest generation attempt.
        if database is None:
            async with lead_repository._memory_lock:
                if site_id in lead_repository._memory:
                    lead_repository._memory[site_id].update({
                        "latestGenerationRunId": run["id"],
                        "pipelineStage": "generating",
                        "pipelineStatusDetail": "Generation in progress",
                        "updatedAt": _now(),
                    })
        else:
            await database["leads"].update_one(
                {"id": site_id},
                {"$set": {
                    "latestGenerationRunId": run["id"],
                    "pipelineStage": "generating",
                    "pipelineStatusDetail": "Generation in progress",
                    "updatedAt": _now(),
                }},
            )
        # Supersede older queued runs with different inputs. Running runs remain
        # historical and are allowed to finish without becoming the latest state.
        if database is not None:
            old_jobs = await database["jobs"].find({"leadId": site_id, "jobType": {"$in": ["site_generate", "site_republish"]}, "status": "queued", "id": {"$ne": job.id}}).to_list(length=50)
            for old_job in old_jobs:
                old_run_id = (old_job.get("metadata") or {}).get("generationRunId")
                if old_run_id:
                    old_run = await self._get_generation_run(old_run_id)
                    if old_run and old_run.get("generationInputHash") != run["generationInputHash"]:
                        reason = supersede_reason(old_run, run)
                        await self._update_generation_run(old_run_id, {"status": "superseded", "supersededByRunId": run["id"], "supersededReason": reason, "finishedAt": _now()})
                        await database["jobs"].update_one({"id": old_job["id"], "status": "queued"}, {"$set": {"status": "failed", "step": "Superseded by newer generation run", "errorMessage": f"superseded:{reason}", "finishedAt": _now(), "updatedAt": _now(), "metadata.supersededByRunId": run["id"], "metadata.supersededReason": reason}})
        # Store the exact run reference and fingerprint on the job itself for old
        # monitoring surfaces and safe task dispatch.
        database = get_database()
        if database is None:
            async with lead_repository._memory_lock:
                if job.id in lead_repository._jobs:
                    lead_repository._jobs[job.id]["metadata"].update({"generationRunId": run["id"], "generationInputHash": run["generationInputHash"], "snapshot": run["snapshot"]})
            old_jobs = [j for j in lead_repository._jobs.values() if site_id in j.get("leadIds", []) and j.get("jobType") in {"site_generate", "site_republish"} and j.get("status") == "queued" and j.get("id") != job.id]
            for old_job in old_jobs:
                old_run_id = (old_job.get("metadata") or {}).get("generationRunId")
                old_run = self._generation_runs.get(old_run_id) if old_run_id else None
                if old_run and old_run.get("generationInputHash") != run["generationInputHash"]:
                    reason = supersede_reason(old_run, run)
                    old_run.update({"status": "superseded", "supersededByRunId": run["id"], "supersededReason": reason, "finishedAt": _now()})
                    old_job.update({"status": "failed", "step": "Superseded by newer generation run", "errorMessage": f"superseded:{reason}", "finishedAt": _now(), "updatedAt": _now()})
        else:
            await database["jobs"].update_one({"id": job.id}, {"$set": {"metadata.generationRunId": run["id"], "metadata.generationInputHash": run["generationInputHash"], "metadata.snapshot": run["snapshot"]}})
        await self._dispatch_generation_job(
            site_id=site_id, job_id=job.id, request=request, generation_run_id=run["id"]
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
        self, *, site_id: str, job_id: str, request: SiteGenerateRequest | None = None,
        generation_run_id: str | None = None,
    ) -> GeneratedSite | None:
        await self._maybe_ensure_indexes()
        run = await self._get_generation_run(generation_run_id) if generation_run_id else None
        if run:
            if run.get("jobId") != job_id or run.get("leadId") != site_id:
                raise ValueError("generation_run_job_or_lead_mismatch")
            if run.get("status") in {"superseded", "cancelled"}:
                logger.warning("Skipping non-executable generation run %s", generation_run_id)
                return None
            snapshot = run["snapshot"]
            await self._update_generation_run(generation_run_id, {"status": "running", "startedAt": run.get("startedAt") or _now()})
        else:
            snapshot = None
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
        master_brief = await (lead_repository.get_master_brief_version(site_id, snapshot["briefId"], snapshot["briefVersion"]) if snapshot else lead_repository.get_master_brief(site_id))
        use_ai_generation = (
            master_brief is not None and master_brief.approvalState == "approved"
        )

        # Phase 3: Legacy briefs deleted; only master_brief now
        if not use_ai_generation:
            raise ValueError("brief_not_approved")
        extraction = await (lead_repository.get_extraction_version(site_id, snapshot["extractionId"], snapshot["extractionVersion"]) if snapshot else lead_repository.get_extraction(site_id))
        if extraction is None or extraction.version <= 0:
            raise ValueError("extraction_required")
        if snapshot and (master_brief is None or master_brief.approvalState != "approved"):
            raise ValueError("pinned_brief_not_approved")

        # High-level generation trace
        logger.info("=== Starting site generation for %s ===", site_id)
        logger.info(
            "AI generation mode: Master brief %s approved",
            master_brief.id if master_brief else "unknown",
        )
        logger.info(
            "Extraction: %d citations, %d brand cues, %d extracted sections",
            len(extraction.sourceCitations),
            len(extraction.brandAssetCues),
            len(getattr(extraction, "sectionInventory", []) or []),
        )

        current = await self.get_site(site_id)
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
                "briefId": master_brief.id if master_brief else "",
                "briefVersion": master_brief.version if master_brief else 0,
                "nextVersion": next_version,
            },
        )

        # AI-native generation from master brief
        if use_ai_generation and master_brief is not None:
            from app.core.ai_site_generation import generate_with_retry

            # Resolve refinement prompt text if a prompt ID was supplied
            refinement_prompt_id = request.refinementPromptId if request else None
            refinement_prompt_text: str | None = None
            if refinement_prompt_id:
                database = get_database()
                if database is not None:
                    site_doc_for_prompt = await database["generated_sites"].find_one(
                        {"id": site_id}
                    )
                    if site_doc_for_prompt:
                        for entry in site_doc_for_prompt.get("promptHistory") or []:
                            if entry.get("id") == refinement_prompt_id:
                                refinement_prompt_text = entry.get("promptText")
                                break
                else:
                    async with self._memory_lock:
                        site_doc_for_prompt = self._sites.get(site_id)
                    if site_doc_for_prompt:
                        for entry in site_doc_for_prompt.get("promptHistory") or []:
                            if entry.get("id") == refinement_prompt_id:
                                refinement_prompt_text = entry.get("promptText")
                                break

            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                progress=40,
                step="Generating landing page code from master brief",
            )

            result = await generate_with_retry(
                master_brief=master_brief,
                extraction=extraction,
                site_id=site_id,
                max_retries=3,
                refinement_prompt=refinement_prompt_text,
            )

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                await lead_repository._update_job(  # noqa: SLF001
                    job_id,
                    status="failed",
                    progress=100,
                    step="Code generation failed",
                    error_message=error_msg,
                    finished=True,
                    lead_ids=[site_id],
                )
                if refinement_prompt_id:
                    await self.update_prompt_result(
                        site_id=site_id,
                        prompt_id=refinement_prompt_id,
                        version_id="",
                        quality_score=0,
                        status="failed",
                        failure_reason=error_msg,
                    )
                return None

            # Persist generated site record to database
            logger.info(
                "Persisting AI-generated site %s version %d", site_id, next_version
            )
            await self._persist_ai_generated_site(
                site_id=site_id,
                job_id=job_id,
                lead=lead,
                master_brief=master_brief,
                extraction=extraction,
                result=result,
                version=next_version,
                current=current,
                refinement_prompt_id=refinement_prompt_id,
                generation_run_id=generation_run_id,
            )

            # Verify site was persisted successfully
            persisted_site = await self.get_site(site_id)
            if persisted_site is None:
                error_msg = f"Site {site_id} not found after persistence"
                logger.error(error_msg)
                await lead_repository._update_job(  # noqa: SLF001
                    job_id,
                    status="failed",
                    progress=100,
                    step="Site persistence verification failed",
                    error_message=error_msg,
                    finished=True,
                    lead_ids=[site_id],
                )
                raise RuntimeError(error_msg)

            if persisted_site.version != next_version:
                error_msg = f"Site {site_id} version mismatch: expected {next_version}, got {persisted_site.version}"
                logger.error(error_msg)
                await lead_repository._update_job(  # noqa: SLF001
                    job_id,
                    status="failed",
                    progress=100,
                    step="Site persistence version mismatch",
                    error_message=error_msg,
                    finished=True,
                    lead_ids=[site_id],
                )
                raise RuntimeError(error_msg)

            logger.info(
                "Successfully verified site %s version %d persistence (quality score: %d)",
                site_id,
                persisted_site.version,
                persisted_site.qualityScore,
            )

            if refinement_prompt_id:
                await self.update_prompt_result(
                    site_id=site_id,
                    prompt_id=refinement_prompt_id,
                    version_id=str(persisted_site.version),
                    quality_score=persisted_site.qualityScore or 0,
                    status="completed",
                )

            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                progress=100,
                step="Generation complete",
                status="completed",
                finished=True,
                lead_ids=[site_id],
            )
            if run:
                await self._update_generation_run(generation_run_id, {"status": "completed", "finishedAt": _now(), "variantResults": [{"variantType": "nextjs", "siteId": persisted_site.id, "status": "completed"}]})
            from app.core.analytics import analytics_repository

            await analytics_repository.record_admin_event(
                event_type="site_generated",
                event_name="Site generated",
                site_id=persisted_site.id,
                lead_id=site_id,
                metadata={
                    "version": persisted_site.version,
                    "qualityScore": persisted_site.qualityScore,
                },
            )
            return persisted_site

    async def queue_refinement_job(
        self,
        site_id: str,
        prompt_text: str,
        operator_id: str,
    ) -> JobSummary | None:
        """Queue a targeted refinement job that edits existing source code in-place."""
        await self._maybe_ensure_indexes()

        current = await self.get_site(site_id)
        if current is None or not current.sourceCode:
            raise ValueError("no_source_code")

        # For multi-variant sites site_id is the variant UUID, leadId is the lead UUID.
        lead_id = current.leadId or site_id
        lead = await lead_repository.get_lead(lead_id)
        if lead is None:
            return None

        master_brief = await lead_repository.get_master_brief(lead_id)
        if master_brief is None or master_brief.approvalState != "approved":
            raise ValueError("brief_not_approved")

        database = get_database()
        if database is not None:
            # Check for existing refinement job for THIS specific site (not all sites for this lead)
            stale_cutoff = _now() - timedelta(minutes=30)
            existing_job = await database["jobs"].find_one(
                {
                    "metadata.siteId": site_id,
                    "jobType": {"$in": ["site_refine"]},
                    "status": {"$in": ["queued", "running"]},
                    "updatedAt": {"$gte": stale_cutoff},
                }
            )
            if existing_job is not None:
                logger.info(
                    "Refinement already in progress for site %s (job %s)",
                    site_id,
                    existing_job["id"],
                )
                return _job_doc_to_summary(existing_job)

        next_version = int(current.version) + 1
        prompt_id = await self.submit_refinement_prompt(
            site_id=site_id,
            prompt_text=prompt_text,
            operator_id=operator_id,
        )
        if prompt_id is None:
            return None

        job = await lead_repository.create_job(
            lead_ids=[lead_id],
            job_type="site_refine",
            status="queued",
            progress=0,
            step="Queued for refinement",
            metadata={
                "siteId": site_id,
                "leadId": lead_id,
                "briefId": master_brief.id,
                "briefVersion": master_brief.version,
                "nextVersion": next_version,
                "promptId": prompt_id,
                "request": {"refinementPromptId": prompt_id},
            },
        )

        settings = get_settings()
        if settings.celery_task_always_eager:
            try:
                await self.run_refinement_job(
                    site_id=site_id,
                    job_id=job.id,
                    prompt_id=prompt_id,
                )
            except Exception:
                logging.getLogger("lenquant.jobs").exception(
                    "Inline refinement job:%s:%s failed", site_id, job.id
                )
                raise
        else:
            from app.core.tasks import run_site_refinement_job_task

            try:
                task_result = run_site_refinement_job_task.delay(  # type: ignore[attr-defined]
                    site_id=site_id, job_id=job.id, prompt_id=prompt_id
                )
                logger.info(
                    "Queued refinement task %s for site %s job %s",
                    task_result.id,
                    site_id,
                    job.id,
                )
            except Exception as exc:
                logger.error(
                    "Failed to queue refinement task for site %s job %s: %s",
                    site_id,
                    job.id,
                    exc,
                    exc_info=True,
                )
                # Update job to failed status
                await lead_repository._update_job(  # noqa: SLF001
                    job.id,
                    status="failed",
                    progress=0,
                    step="Failed to queue refinement task",
                    error_message=f"Task queueing failed: {exc}",
                    finished=True,
                    lead_ids=[lead_id],
                )
                raise

        return job

    async def run_refinement_job(
        self, *, site_id: str, job_id: str, prompt_id: str
    ) -> GeneratedSite | None:
        """Apply targeted operator refinement to existing source code."""
        await self._maybe_ensure_indexes()
        from app.core.ai_site_generation import refine_with_retry

        current = await self.get_site(site_id)
        if current is None or not current.sourceCode:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="No source code to refine",
                error_message="Site has no generated source code",
                finished=True,
                lead_ids=[site_id],
            )
            return None

        # Resolve the lead using leadId from the site (site_id may be a variant UUID)
        lead_id = current.leadId or site_id
        lead = await lead_repository.get_lead(lead_id)
        if lead is None:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Lead missing for refinement",
                error_message="Lead not found",
                finished=True,
                lead_ids=[lead_id],
            )
            return None

        # Resolve prompt text
        prompt_text: str | None = None
        database = get_database()
        if database is not None:
            site_doc = await database["generated_sites"].find_one({"id": site_id})
            if site_doc:
                for entry in site_doc.get("promptHistory") or []:
                    if entry.get("id") == prompt_id:
                        prompt_text = entry.get("promptText")
                        break
        else:
            async with self._memory_lock:
                site_doc = self._sites.get(site_id)
            if site_doc:
                for entry in site_doc.get("promptHistory") or []:
                    if entry.get("id") == prompt_id:
                        prompt_text = entry.get("promptText")
                        break

        if not prompt_text:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Prompt not found",
                error_message=f"Refinement prompt {prompt_id} not found",
                finished=True,
                lead_ids=[lead_id],
            )
            return None

        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            status="running",
            progress=30,
            step="Applying refinement to site code",
            lead_ids=[lead_id],
            metadata={
                "siteId": site_id,
                "leadId": lead_id,
                "promptId": prompt_id,
                "nextVersion": current.version + 1,
            },
        )

        result = await refine_with_retry(
            site_id=site_id,
            current_source_code=current.sourceCode,
            refinement_prompt=prompt_text,
            variant_type=current.variantType or "nextjs",
        )

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Refinement failed",
                error_message=error_msg,
                finished=True,
                lead_ids=[lead_id],
            )
            await self.update_prompt_result(
                site_id=site_id,
                prompt_id=prompt_id,
                version_id="",
                quality_score=0,
                status="failed",
                failure_reason=error_msg,
            )
            return None

        master_brief = await lead_repository.get_master_brief(lead_id)
        extraction = await lead_repository.get_extraction(lead_id)
        if master_brief is None or extraction is None:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Brief or extraction missing after refinement",
                error_message="Cannot persist refined site without brief/extraction",
                finished=True,
                lead_ids=[lead_id],
            )
            return None

        next_version = current.version + 1
        await self._persist_ai_generated_site(
            site_id=site_id,
            job_id=job_id,
            lead=lead,
            master_brief=master_brief,
            extraction=extraction,
            result=result,
            version=next_version,
            current=current,
            refinement_prompt_id=prompt_id,
        )

        persisted_site = await self.get_site(site_id)
        if persisted_site is None:
            error_msg = f"Site {site_id} not found after refinement persistence"
            logger.error(error_msg)
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Site persistence verification failed",
                error_message=error_msg,
                finished=True,
                lead_ids=[lead_id],
            )
            raise RuntimeError(error_msg)

        await self.update_prompt_result(
            site_id=site_id,
            prompt_id=prompt_id,
            version_id=str(persisted_site.version),
            quality_score=persisted_site.qualityScore or 0,
            status="completed",
        )

        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            progress=100,
            step="Refinement complete",
            status="completed",
            finished=True,
            lead_ids=[lead_id],
        )
        from app.core.analytics import analytics_repository

        await analytics_repository.record_admin_event(
            event_type="generation_regenerated",
            event_name="Site refined",
            site_id=persisted_site.id,
            lead_id=lead_id,
            metadata={"version": persisted_site.version, "promptId": prompt_id},
        )
        return persisted_site

    async def _persist_ai_generated_site(
        self,
        *,
        site_id: str,
        job_id: str,
        lead: Any,
        master_brief: Any,
        extraction: ExtractionSnapshot,
        result: dict[str, Any],
        version: int,
        current: GeneratedSite | None,
        refinement_prompt_id: str | None = None,
        generation_run_id: str | None = None,
    ) -> None:
        """Persist generated site record after successful AI code generation."""
        now = _now()
        settings = get_settings()

        signals = " ".join(
            [
                _text(lead.companyName),
                _text(getattr(lead, "industry", None)),
                _text(master_brief.valueProposition),
                _text(master_brief.primaryAudience),
                _text(master_brief.toneAndVoice),
                _text(master_brief.conversionAction),
                _text(extraction.summary.positioningSummary),
                " ".join(extraction.summary.toneClues),
                " ".join(cue.label for cue in extraction.brandAssetCues),
                " ".join(cue.value for cue in extraction.brandAssetCues),
            ]
        )
        theme, theme_rationale = _theme_for_signals(signals, extraction)
        palette_mode, palette_rationale = _palette_mode_from_signals(
            " ".join(
                [
                    _text(master_brief.toneAndVoice),
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

        default_evidence = {
            "sourceKind": "extraction",
            "inferenceLabel": "AI-generated",
            "confidence": 80,
            "references": [],
        }
        approved_tokens = self._brand_tokens_from_brief(master_brief).model_dump()
        brand_tokens = {
            "paletteMode": palette_mode,
            "primaryColor": {"value": "#1a1a2e", "evidence": default_evidence},
            "secondaryColor": {"value": "#16213e", "evidence": default_evidence},
            "accentColor": {"value": "#0f3460", "evidence": default_evidence},
            "backgroundColor": {"value": "#ffffff", "evidence": default_evidence},
            "textColor": {"value": "#1a1a2e", "evidence": default_evidence},
            "borderColor": {"value": "#e2e8f0", "evidence": default_evidence},
            "typography": {
                "value": "system-ui, sans-serif",
                "evidence": default_evidence,
            },
            "imageStyle": {"value": "clean", "evidence": default_evidence},
            "visualTone": {
                "value": master_brief.visualStyle or "modern",
                "evidence": default_evidence,
            },
            "motionIntensity": {
                "value": master_brief.motionLevel or "subtle",
                "evidence": default_evidence,
            },
            "layoutDensity": {"value": "balanced", "evidence": default_evidence},
        }
        # Approved brand assets are the source of truth for every generation run.
        for token_name in ("primaryColor", "secondaryColor", "accentColor", "typography"):
            if approved_tokens.get(token_name):
                brand_tokens[token_name] = approved_tokens[token_name]
        if approved_tokens.get("logoAsset"):
            brand_tokens["logoAsset"] = approved_tokens["logoAsset"]

        hero_variant = {
            "headline": master_brief.headline,
            "subheadline": master_brief.subheadline,
            "supportingLine": master_brief.valueProposition,
            "primaryCta": master_brief.ctaStrategy,
            "secondaryCta": "Learn more",
            "layout": theme.get("heroFamily", "stacked-panel"),
            "visualTreatment": master_brief.visualStyle or "modern",
            "evidence": default_evidence,
        }

        # Generate or reuse preview slug
        if current and current.previewSlug:
            preview_slug = current.previewSlug
        else:
            all_sites = await self._list_sites(limit=200, offset=0)
            existing_slugs = {s.previewSlug for s in all_sites}
            preview_slug = _generate_friendly_slug(
                lead.companyName or site_id, existing_slugs
            )

        preview_url = f"{settings.preview_base_url}/{preview_slug}"

        source_attribution = _site_source_attribution(
            lead=lead,
            brief=master_brief,
            extraction=extraction,
            theme=theme,
            palette_mode=palette_mode,
        )

        missing_reqs = list(master_brief.missingRequirements or [])
        generated_sections = self._master_section_stack(master_brief, extraction)
        generated_cta = self._master_cta_strategy(master_brief)
        computed_quality_score = _quality_score(
            brief=master_brief,
            extraction=extraction,
            brand_tokens=brand_tokens,
            site_sections=generated_sections,
            missing_requirements=missing_reqs,
        )
        settings_for_readiness = get_settings()
        readiness_threshold = int(
            settings_for_readiness.visual_redesign_quality_threshold or 90
        )
        review_floor = max(70, readiness_threshold - 15)
        if computed_quality_score >= readiness_threshold and not missing_reqs:
            computed_readiness: SiteReadinessStatus = "ready_to_publish"
            computed_qa: SiteQaStatus = "pass"
        elif computed_quality_score >= review_floor and len(missing_reqs) <= 2:
            computed_readiness = "ready_for_review"
            computed_qa = "warn"
        elif computed_quality_score >= 55:
            computed_readiness = "needs_review"
            computed_qa = "warn"
        else:
            computed_readiness = "blocked"
            computed_qa = "fail"

        site_doc: dict[str, Any] = {
            "id": site_id,
            "leadId": lead.id,
            "generationJobId": job_id,
            "generationRunId": generation_run_id,
            "briefId": master_brief.id,
            "briefVersion": master_brief.version,
            "variantBriefId": master_brief.id if generation_run_id is None else f"{generation_run_id}:nextjs",
            "variantBriefVersion": master_brief.version,
            "extractionId": extraction.id,
            "extractionVersion": extraction.version,
            "brandRevision": int(getattr(master_brief, "brandRevision", 1) or 1),
            "brandSnapshotHash": brand_snapshot_hash(master_brief.brandAssets.model_dump(mode="json")),
            "generationInputHash": ((await self._get_generation_run(generation_run_id) or {}).get("generationInputHash") if generation_run_id else None),
            "generatorVersion": "generation-run-v1",
            "promptVersion": "master-brief-v1",
            "version": version,
            "themeId": theme["id"],
            "themeKey": theme["themeKey"],
            "themeName": theme["name"],
            "themeRationale": theme_rationale,
            "paletteMode": palette_mode,
            "paletteRationale": palette_rationale,
            "brandTokens": brand_tokens,
            "heroVariant": hero_variant,
            "sectionStack": generated_sections,
            "ctaStrategy": generated_cta,
            "qualityScore": computed_quality_score,
            "qualityScoreSource": "fallback",
            "readinessStatus": computed_readiness,
            "qaStatus": computed_qa,
            "reviewRubric": [],
            "comparisonEntries": [],
            "sourceTraceability": [],
            "missingRequirements": list(master_brief.missingRequirements or []),
            "sourceAttribution": source_attribution,
            "browserReviewState": "not_reviewed",
            "publishApprovalState": "pending",
            "screenshotRefs": [],
            "diversityNotes": [],
            "diversityScore": 50,
            "layoutHash": "",
            "previewSlug": preview_slug,
            "previewUrl": preview_url,
            "overrideCount": 0,
            "overrides": [],
            "overrideDiffs": [],
            "refinementPromptId": refinement_prompt_id,
            "promptHistory": [
                (r.model_dump() if hasattr(r, "model_dump") else r)
                for r in (current.promptHistory or [])
            ]
            if current
            else [],
            "isManuallyRefined": refinement_prompt_id is not None,
            "improvementRecommendations": None,
            "sourceCode": result.get("sourceCode"),
            "compiledBundleUrl": result.get("compiledBundleUrl"),
            "compilationStatus": result.get("compilationStatus", "success"),
            "compilationError": None,
            "createdAt": current.createdAt if current else now,
            "updatedAt": now,
        }

        # Apply any active structured overrides to the site doc before persisting
        active_overrides = await self._site_overrides(site_id)
        if active_overrides:
            site_doc["heroVariant"] = self._apply_hero_overrides(
                site_doc["heroVariant"], active_overrides
            )
            site_doc["ctaStrategy"] = self._apply_cta_overrides(
                site_doc["ctaStrategy"], active_overrides
            )
            site_doc["brandTokens"] = self._apply_brand_overrides(
                site_doc["brandTokens"], active_overrides
            )
            site_doc["sectionStack"] = self._apply_overrides(
                site_doc["sectionStack"], active_overrides
            )
            site_doc["overrideCount"] = len(active_overrides)

        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._sites[site_id] = site_doc
            logger.info(
                "Persisted AI-generated site %s version %d (in-memory)",
                site_id,
                version,
            )
            return

        # Persist to MongoDB with upsert
        db_result: UpdateResult = await database["generated_sites"].replace_one(
            {"id": site_id}, site_doc, upsert=True
        )

        # CRITICAL FIX: Verify persistence succeeded
        if db_result.matched_count == 0 and db_result.upserted_id is None:
            error_msg = f"Failed to persist site {site_id} version {version}: replace_one returned no match or upsert"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Verify the site can be retrieved
        verification = await database["generated_sites"].find_one({"id": site_id})
        if verification is None:
            error_msg = f"Site {site_id} version {version} not found after persistence"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        persisted_version = verification.get("version", 0)
        if persisted_version != version:
            error_msg = f"Version mismatch for site {site_id}: expected {version}, got {persisted_version}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(
            "Successfully persisted AI-generated site %s version %d (MongoDB, matched=%d, upserted=%s)",
            site_id,
            version,
            db_result.matched_count,
            db_result.upserted_id is not None,
        )

    async def _dispatch_generation_job(
        self, *, site_id: str, job_id: str, request: SiteGenerateRequest | None,
        generation_run_id: str | None = None,
    ) -> None:
        settings = get_settings()

        # Check if multi-variant generation is requested
        variant_types = request.variantTypes if request else None
        if variant_types:
            # Use multi-variant generation task
            if settings.celery_task_always_eager:
                from app.core.tasks import _run_multi_variant_generation_async

                try:
                    await _run_multi_variant_generation_async(
                        lead_id=site_id,
                        job_id=job_id,
                        generation_types=list(variant_types),
                        generation_run_id=generation_run_id,
                    )
                except Exception:  # pragma: no cover - eager path logging
                    logging.getLogger("lenquant.jobs").exception(
                        "Inline multi-variant generation:%s:%s failed", site_id, job_id
                    )
                    raise
                return

            from app.core.tasks import run_multi_variant_generation_task

            run_multi_variant_generation_task.delay(  # type: ignore[attr-defined]
                lead_id=site_id, job_id=job_id, generation_types=list(variant_types), generation_run_id=generation_run_id
            )
            return

        # Default single-site generation
        if settings.celery_task_always_eager:
            try:
                await self.run_generation_job(
                    site_id=site_id, job_id=job_id, request=request, generation_run_id=generation_run_id
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
            site_id=site_id, job_id=job_id, request_payload=payload, generation_run_id=generation_run_id
        )

    async def run_republish_job(self, *, site_id: str, job_id: str) -> None:
        """Recompile existing sourceCode and re-upload to S3 without calling the LLM."""
        from app.core.ai_site_generation import _upload_bundle_to_s3
        from app.core.compiler_client import CompilerError, get_compiler_client

        site = await self.get_site(site_id)
        if site is None:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Site not found",
                error_message="Site not found",
                finished=True,
                lead_ids=[site_id],
            )
            return

        source_code = site.sourceCode
        if not source_code:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="No source code to recompile",
                error_message="Site has no sourceCode to recompile",
                finished=True,
                lead_ids=[site_id],
            )
            return

        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            status="running",
            progress=30,
            step="Recompiling existing source code",
            lead_ids=[site_id],
        )

        compiler = get_compiler_client()
        try:
            compile_result = await compiler.compile_tsx(
                source_code=source_code,
                component_name=f"LandingPage_{site_id}",
                site_id=site_id,
            )
        except CompilerError as exc:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Compilation error",
                error_message=str(exc),
                finished=True,
                lead_ids=[site_id],
            )
            return

        if not compile_result.get("success"):
            error_msg = compile_result.get("error", "Compilation failed")
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="Compilation failed",
                error_message=error_msg,
                finished=True,
                lead_ids=[site_id],
            )
            return

        bundle_code = compile_result.get("bundleCode")
        css_code = compile_result.get("cssCode")
        if not bundle_code:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="No bundle produced",
                error_message="Compilation succeeded but returned no bundle",
                finished=True,
                lead_ids=[site_id],
            )
            return

        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            status="running",
            progress=70,
            step="Uploading bundle to S3",
            lead_ids=[site_id],
        )

        try:
            bundle_url = _upload_bundle_to_s3(bundle_code, css_code, site_id)
        except Exception as exc:
            await lead_repository._update_job(  # noqa: SLF001
                job_id,
                status="failed",
                progress=100,
                step="S3 upload failed",
                error_message=str(exc),
                finished=True,
                lead_ids=[site_id],
            )
            return

        now = _now()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["compiledBundleUrl"] = bundle_url
                    doc["compilationStatus"] = "success"
                    doc["compilationError"] = None
                    doc["updatedAt"] = now
        else:
            await database["generated_sites"].update_one(
                {"id": site_id},
                {
                    "$set": {
                        "compiledBundleUrl": bundle_url,
                        "compilationStatus": "success",
                        "compilationError": None,
                        "updatedAt": now,
                    }
                },
            )

        await lead_repository._update_job(  # noqa: SLF001
            job_id,
            status="completed",
            progress=100,
            step="Republish complete",
            finished=True,
            lead_ids=[site_id],
        )
        from app.core.analytics import analytics_repository

        await analytics_repository.record_admin_event(
            event_type="site_republished",
            event_name="Site republished",
            site_id=site_id,
            lead_id=site_id,
            metadata={"bundleUrl": bundle_url},
        )

    async def queue_republish_job(self, site_id: str) -> JobSummary | None:
        """Queue a lightweight republish job that recompiles without LLM generation."""
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None

        database = get_database()
        if database is not None:
            existing = await database["jobs"].find_one(
                {
                    "leadId": site_id,
                    "jobType": {"$in": ["site_republish"]},
                    "status": {"$in": ["queued", "running"]},
                }
            )
            if existing is not None:
                return _job_doc_to_summary(existing)

        job = await lead_repository.create_job(
            lead_ids=[site_id],
            job_type="site_republish",
            status="queued",
            progress=0,
            step="Queued for republish",
            metadata={"siteId": site_id, "leadId": site_id},
        )

        settings = get_settings()
        if settings.celery_task_always_eager:
            await self.run_republish_job(site_id=site_id, job_id=job.id)
            return job

        from app.core.tasks import run_site_republish_task

        run_site_republish_task.delay(site_id=site_id, job_id=job.id)  # type: ignore[attr-defined]
        return job

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

    async def _backfill_source_attribution(
        self, sites: list[GeneratedSite]
    ) -> list[GeneratedSite]:
        """For sites with no sourceAttribution, fetch lead names in one batch query."""
        missing = [
            s
            for s in sites
            if not s.sourceAttribution or not s.sourceAttribution.companyName
        ]
        if not missing:
            return sites
        lead_ids = list({s.leadId for s in missing})
        database = get_database()
        lead_names: dict[str, str] = {}
        if database is not None:
            cursor = database["leads"].find({"id": {"$in": lead_ids}})
            lead_docs = await cursor.to_list(length=len(lead_ids))
            for doc in lead_docs:
                lead_id = doc.get("id", "")
                name = doc.get("companyName") or doc.get("normalizedDomain") or ""
                if lead_id and name:
                    lead_names[lead_id] = name
        for site in missing:
            name = lead_names.get(site.leadId)
            if name:
                if site.sourceAttribution is None:
                    site.sourceAttribution = SiteSourceAttribution(
                        leadId=site.leadId, companyName=name
                    )
                else:
                    site.sourceAttribution = site.sourceAttribution.model_copy(
                        update={"companyName": name}
                    )
        return sites

    async def list_sites(
        self, *, limit: int = 25, offset: int = 0, user_id: str | None = None
    ) -> list[GeneratedSite]:
        sites = await self._list_sites(limit=limit, offset=offset, user_id=user_id)
        return await self._backfill_source_attribution(sites)

    async def _list_sites(
        self, *, limit: int, offset: int, user_id: str | None = None
    ) -> list[GeneratedSite]:
        database = get_database()
        query: dict[str, Any] = {}
        if user_id:
            query["userId"] = user_id
        if database is None:
            async with self._memory_lock:
                docs = [
                    doc
                    for doc in self._sites.values()
                    if not user_id or doc.get("userId") == user_id
                ]
                docs.sort(key=lambda item: item.get("updatedAt", _now()), reverse=True)
                return [
                    _site_doc_to_current(doc) for doc in docs[offset : offset + limit]
                ]
        cursor = (
            database["generated_sites"]
            .find(query)
            .sort("updatedAt", -1)
            .skip(offset)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [_site_doc_to_current(doc) for doc in docs]

    async def _count_sites(self, user_id: str | None = None) -> int:
        database = get_database()
        query: dict[str, Any] = {}
        if user_id:
            query["userId"] = user_id
        if database is None:
            async with self._memory_lock:
                if user_id:
                    return sum(
                        1
                        for doc in self._sites.values()
                        if doc.get("userId") == user_id
                    )
                return len(self._sites)
        return await database["generated_sites"].count_documents(query)

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
