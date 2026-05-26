from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.schemas.brief import SiteBrief
from app.schemas.extraction import ExtractionSnapshot
from app.schemas.site import (
    GeneratedSite,
    GeneratedSiteVersion,
    GeneratedSiteVersionResponse,
    PublishApprovalState,
    PaletteMode,
    ReviewWorkflowState,
    SiteExportMetadata,
    SiteHandoffRecord,
    SiteGenerateRequest,
    SiteReviewChecklistItem,
    SiteReviewQueueItem,
    SiteReviewQueueResponse,
    SiteReviewRecord,
    SiteReviewRequest,
    SiteReviewPatchRequest,
    SiteScreenshotMetadata,
    SiteSourceAttribution,
    SiteOverrideCreateRequest,
    SiteOverrideRecord,
    SiteQaStatus,
    SiteReadinessStatus,
    ThemeLibraryResponse,
    ThemeVariant,
    SiteCompareResponse,
)

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
        "bestForIndustries": ["real estate", "hospitality", "premium services", "advisory"],
        "placeholderPolicy": "No placeholder metrics, testimonials, or demo imagery.",
        "allowedPaletteModes": ["zinc", "light"],
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _theme_for_signals(signals: str, extraction: ExtractionSnapshot) -> tuple[dict[str, Any], str]:
    theme_scores = {theme["themeKey"]: 0 for theme in THEME_LIBRARY}
    if _contains_any(signals, ["premium", "executive", "authority", "consulting", "finance", "law"]):
        theme_scores["editorial-frame"] += 4
    if _contains_any(signals, ["conversion", "lead", "book", "demo", "call", "performance", "growth"]):
        theme_scores["signal-panel"] += 4
    if _contains_any(signals, ["creative", "brand", "visual", "studio", "color", "design"]):
        theme_scores["color-study"] += 4
    if _contains_any(signals, ["minimal", "clean", "quiet", "refined", "luxe", "premium"]):
        theme_scores["minimal-luxe"] += 4
    if extraction.brandAssetCues:
        color_cues = [cue for cue in extraction.brandAssetCues if cue.assetType == "color"]
        if color_cues:
            if len(color_cues) >= 2 or any(_contains_any(f"{cue.label} {cue.value}", ["vibrant", "gradient", "multi", "colorful"]) for cue in color_cues):
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


def _palette_mode_from_signals(signals: str, extraction: ExtractionSnapshot) -> tuple[PaletteMode, str]:
    color_text = " ".join(f"{cue.label} {cue.value} {cue.note or ''}" for cue in extraction.brandAssetCues if cue.assetType == "color").lower()
    if _contains_any(color_text or signals, ["vibrant", "bright", "gradient", "multi", "colorful", "bold"]):
        return "colorful", "The source brand cues contain enough color energy to support a more expressive palette."
    if _contains_any(color_text or signals, ["monochrome", "neutral", "minimal", "zinc", "grayscale", "grey", "gray", "black", "white"]):
        return "zinc", "The source site reads as restrained and neutral, so a zinc palette keeps the preview aligned."
    if _contains_any(signals, ["premium", "advisory", "enterprise", "clean", "refined"]):
        return "light", "The source language suggests a clean, premium treatment without pushing into a dark monochrome system."
    return "light", "No strong chromatic cues were available, so the preview stays in a light palette with explicit inference labels."


def _confidence(*scores: int, floor: int = 0, ceiling: int = 95) -> int:
    values = [int(score) for score in scores if score is not None]
    if not values:
        return floor
    return max(floor, min(ceiling, round(sum(values) / len(values))))


def _site_refs(brief: SiteBrief, extraction: ExtractionSnapshot) -> list[dict[str, Any]]:
    refs = [_page_reference_from_citation(citation.model_dump() if hasattr(citation, "model_dump") else citation) for citation in extraction.sourceCitations]
    refs.extend(_asset_reference_from_cue(cue.model_dump() if hasattr(cue, "model_dump") else cue) for cue in extraction.brandAssetCues)
    refs.extend(citation.model_dump() if hasattr(citation, "model_dump") else citation for citation in brief.sourceCitations)
    return _dedupe_refs(refs)


def _brand_tokens(
    *,
    palette_mode: PaletteMode,
    theme: dict[str, Any],
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    color_cues = [cue.model_dump() if hasattr(cue, "model_dump") else cue for cue in extraction.brandAssetCues if cue.assetType == "color"]
    logo_cues = [cue.model_dump() if hasattr(cue, "model_dump") else cue for cue in extraction.brandAssetCues if cue.assetType == "logo"]
    typography_cues = [cue.model_dump() if hasattr(cue, "model_dump") else cue for cue in extraction.brandAssetCues if cue.assetType == "typography"]
    image_cues = [cue.model_dump() if hasattr(cue, "model_dump") else cue for cue in extraction.brandAssetCues if cue.assetType == "image"]
    tone_text = " ".join(extraction.summary.toneClues[:3]) or _text(brief.toneProfile.value)
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
    if color_cues:
        first = color_cues[0]
        primary_value = _text(first["value"])
        primary_refs = [_asset_reference_from_cue(first)]
        if len(color_cues) > 1:
            secondary_value = _text(color_cues[1]["value"])
            secondary_refs = [_asset_reference_from_cue(color_cues[1])]
        else:
            secondary_value = palette_defaults["accent"]
            secondary_refs = color_reference
        accent_value = _text(color_cues[2]["value"]) if len(color_cues) > 2 else palette_defaults["accent"]
        accent_refs = [_asset_reference_from_cue(color_cues[2])] if len(color_cues) > 2 else color_reference
    else:
        primary_value = palette_defaults["accent"] if palette_mode == "colorful" else "#475569"
        secondary_value = "#94a3b8" if palette_mode == "zinc" else "#64748b"
        accent_value = palette_defaults["accent"]
        primary_refs = color_reference
        secondary_refs = color_reference
        accent_refs = color_reference

    logo_value = logo_cues[0]["label"] if logo_cues else "No logo asset captured"
    logo_kind = "source_backed" if logo_cues else "inferred"
    logo_refs = [_asset_reference_from_cue(logo_cues[0])] if logo_cues else refs[:1]
    typography_value = typography_cues[0]["value"] if typography_cues else theme["typographyPairing"]
    typography_kind = "source_backed" if typography_cues else "inferred"
    typography_refs = [_asset_reference_from_cue(typography_cues[0])] if typography_cues else refs[:2]
    image_value = image_cues[0]["label"] if image_cues else "No image direction captured"
    image_kind = "source_backed" if image_cues else "inferred"
    image_refs = [_asset_reference_from_cue(image_cues[0])] if image_cues else refs[:2]
    visual_tone_value = tone_text or brief.toneProfile.value
    visual_tone_kind = "source_backed" if extraction.summary.toneClues else "inferred"
    visual_tone_refs = refs[:3]
    motion_value = theme["motionPreset"]
    motion_kind = "inferred"
    layout_value = theme["spacingStyle"]
    layout_kind = "inferred"
    return {
        "paletteMode": palette_mode,
        "primaryColor": _token(
            primary_value,
            source_kind="source_backed" if color_cues else "inferred",
            inference_label="Taken directly from extracted brand color cues." if color_cues else "Derived from the selected palette and theme.",
            confidence=_confidence(*(cue["confidence"] for cue in color_cues[:2]), floor=55 if color_cues else 36),
            references=primary_refs,
        ),
        "secondaryColor": _token(
            secondary_value,
            source_kind="source_backed" if len(color_cues) > 1 else "inferred",
            inference_label="Taken from the second captured brand color." if len(color_cues) > 1 else "Derived from the selected palette and theme.",
            confidence=_confidence(*(cue["confidence"] for cue in color_cues[1:3]), floor=52 if len(color_cues) > 1 else 34),
            references=secondary_refs,
        ),
        "accentColor": _token(
            accent_value,
            source_kind="source_backed" if len(color_cues) > 2 else "inferred",
            inference_label="Taken from the extracted accent color cue." if len(color_cues) > 2 else "Derived from the palette mode and theme direction.",
            confidence=_confidence(*(cue["confidence"] for cue in color_cues[2:3]), floor=50 if len(color_cues) > 2 else 34),
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
            inference_label="Captured from the public logo asset." if logo_cues else "No logo asset was captured, so the preview marks the gap explicitly.",
            confidence=_confidence(*(cue["confidence"] for cue in logo_cues[:1]), floor=40 if logo_cues else 20),
            references=logo_refs,
        ),
        "typography": _token(
            typography_value,
            source_kind=typography_kind,
            inference_label="Captured from the public typography cue." if typography_cues else "Derived from the selected theme pairing because the source typography cue was sparse.",
            confidence=_confidence(*(cue["confidence"] for cue in typography_cues[:1]), floor=42 if typography_cues else 28),
            references=typography_refs,
        ),
        "imageStyle": _token(
            image_value,
            source_kind=image_kind,
            inference_label="Captured from the public image cue." if image_cues else "Derived from the source visual language because no clear image direction was extracted.",
            confidence=_confidence(*(cue["confidence"] for cue in image_cues[:1]), floor=38 if image_cues else 24),
            references=image_refs,
        ),
        "visualTone": _token(
            visual_tone_value,
            source_kind=visual_tone_kind,
            inference_label="Taken from the extraction tone cues." if extraction.summary.toneClues else "Derived from the approved brief tone profile.",
            confidence=_confidence(*(citation["confidence"] for citation in refs[:3]), floor=54 if extraction.summary.toneClues else 30),
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
    }


def _hero_variant(
    *,
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    theme: dict[str, Any],
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    headline_source = _text(brief.recommendedHero.value) or _text(brief.companySummary.value) or (brief.companySummary.evidence.inferenceLabel if brief.companySummary else "")
    if not headline_source:
        headline_source = f"Make {brief.companySummary.value if brief.companySummary.value else 'the site'} easier to trust and act on."
    supporting = _text(brief.conversionAngle.value) or _text(extraction.summary.positioningSummary) or "The approved brief is sparse enough that the preview keeps the gap explicit."
    subheadline = _text(brief.audienceHypothesis.value) or "Audience hypothesis remains an inference until the operator revisits the brief."
    primary_cta = "Review the preview"
    secondary_cta = "See source notes"
    if _contains_any(supporting, ["book", "call", "demo", "consult", "review"]):
        primary_cta = "Book a call"
        secondary_cta = "See the brief"
    elif _contains_any(supporting, ["contact", "inquiry", "estimate", "quote"]):
        primary_cta = "Request a quote"
        secondary_cta = "See the source trace"
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
            inference_label="Hero direction is derived from the approved brief." if brief.recommendedHero.value else "Hero is inferred from the company summary and conversion angle.",
            confidence=_confidence(brief.recommendedHero.evidence.confidence, brief.conversionAngle.evidence.confidence, floor=48),
            references=refs[:3],
        ),
    }


def _section_stack(
    *,
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    section_refs = refs[:4]
    if brief.recommendedSections:
        for index, recommendation in enumerate(brief.recommendedSections[:5], start=1):
            sections.append(
                {
                    "kind": "section",
                    "title": recommendation.title,
                    "eyebrow": f"Section {index}",
                    "headline": recommendation.title,
                    "body": recommendation.rationale,
                    "items": [recommendation.evidence.inferenceLabel],
                    "ctaLabel": None,
                    "evidence": recommendation.evidence.model_dump() if hasattr(recommendation.evidence, "model_dump") else recommendation.evidence,
                }
            )
    else:
        sections.append(
            {
                "kind": "gap",
                "title": "Open questions",
                "eyebrow": "Missing data",
                "headline": "The source brief still has unresolved gaps.",
                "body": "This section stays explicit about the missing evidence instead of inventing filler content.",
                "items": list(extraction.gapItems[:4]) or ["No section guidance was available in the approved brief."],
                "ctaLabel": None,
                "evidence": _brief_evidence(
                    source_kind="inferred",
                    inference_label="Derived from the missing requirements list.",
                    confidence=48,
                    references=section_refs,
                ),
            }
        )

    proof_points = list(brief.proofPoints[:3])
    if proof_points:
        sections.append(
            {
                "kind": "proof",
                "title": "Proof points",
                "eyebrow": "Source-backed",
                "headline": "What the source already proves",
                "body": "The preview highlights only the proof points that were actually extracted or approved.",
                "items": [f"{proof.label}: {proof.detail}" for proof in proof_points],
                "ctaLabel": None,
                "evidence": _brief_evidence(
                    source_kind="source_backed",
                    inference_label="Proof points are copied from the approved brief.",
                    confidence=_confidence(*(proof.evidence.confidence for proof in proof_points), floor=58),
                    references=section_refs,
                ),
            }
        )

    sections.append(
        {
            "kind": "cta",
            "title": "Call to action",
            "eyebrow": "Conversion",
            "headline": brief.conversionAngle.value,
            "body": "The CTA stays grounded in the approved conversion angle and the public evidence that supported it.",
            "items": [],
            "ctaLabel": "Review the preview",
            "evidence": _brief_evidence(
                source_kind="source_backed" if brief.conversionAngle.value else "inferred",
                inference_label="CTA section is derived from the approved brief conversion angle.",
                confidence=_confidence(brief.conversionAngle.evidence.confidence, floor=52),
                references=section_refs[:2],
            ),
        }
    )
    return sections


def _cta_strategy(brief: SiteBrief, extraction: ExtractionSnapshot, refs: list[dict[str, Any]]) -> dict[str, Any]:
    primary = "Book a call"
    secondary = "Review the preview"
    footer = "See the source notes"
    rationale = _text(brief.conversionAngle.value) or "Conversion angle remains an inferred review point."
    if _contains_any(rationale, ["quote", "estimate", "proposal"]):
        primary = "Request a quote"
        secondary = "Review the brief"
        footer = "See the source notes"
    elif _contains_any(rationale, ["book", "call", "meeting", "demo", "consult"]):
        primary = "Book a call"
        secondary = "Review the preview"
        footer = "See the source notes"
    elif _contains_any(rationale, ["learn", "discover", "explore"]):
        primary = "Explore the preview"
        secondary = "See source traceability"
        footer = "Review the brief"
    return {
        "primary": _brief_action(primary, "#contact", rationale, refs[:2], brief.conversionAngle.evidence.confidence),
        "secondary": _brief_action(secondary, "#sections", "Keeps a lower-friction path visible for operators reviewing the preview.", refs[:2], max(brief.conversionAngle.evidence.confidence - 10, 40)),
        "footer": _brief_action(footer, "#source-notes", "Keeps source review close to the CTA so the operator can verify it quickly.", refs[:2], 58),
    }


def _brief_action(label: str, href: str, rationale: str, refs: list[dict[str, Any]], confidence: int) -> dict[str, Any]:
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
            "notes": "No placeholder copy, fake metrics, or demo filler is present in the generated sections." if not has_placeholders else "The generated output contains placeholder-like language and should not be published.",
            "evidence": None,
        }
    )
    traceable_tokens = [brand_tokens["primaryColor"], brand_tokens["accentColor"], brand_tokens["typography"]]
    checks.append(
        {
            "key": "brand_traceability",
            "label": "Brand traceability",
            "status": "pass" if any(token["evidence"]["sourceKind"] == "source_backed" for token in traceable_tokens) else "warn",
            "notes": "At least one of the core brand tokens is grounded in extracted source cues." if any(token["evidence"]["sourceKind"] == "source_backed" for token in traceable_tokens) else "Brand tokens are mostly inferred because the source cues were sparse.",
            "evidence": traceable_tokens[0]["evidence"],
        }
    )
    checks.append(
        {
            "key": "palette_fit",
            "label": "Palette mode fit",
            "status": "pass" if palette_mode in {"zinc", "light", "colorful"} else "fail",
            "notes": f"The preview uses the {palette_mode} palette because the source visual language supported it.",
            "evidence": brand_tokens["backgroundColor"]["evidence"],
        }
    )
    checks.append(
        {
            "key": "cta_clarity",
            "label": "CTA clarity",
            "status": "pass" if _text(brief.conversionAngle.value) else "warn",
            "notes": "A primary CTA and a lower-friction secondary CTA are visible in the preview." if _text(brief.conversionAngle.value) else "The conversion angle is too sparse to fully validate the CTA plan.",
            "evidence": brief.conversionAngle.evidence.model_dump() if hasattr(brief.conversionAngle.evidence, "model_dump") else brief.conversionAngle.evidence,
        }
    )
    checks.append(
        {
            "key": "screenshot_ready",
            "label": "Screenshot QA ready",
            "status": "warn" if extraction.confidenceScore < 60 else "pass",
            "notes": "The preview can be reviewed in-browser and captured for visual QA; low-confidence sources should be inspected before publish.",
            "evidence": brief.conversionAngle.evidence.model_dump() if hasattr(brief.conversionAngle.evidence, "model_dump") else brief.conversionAngle.evidence,
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
) -> int:
    score = 50
    if brief.approvalState == "approved":
        score += 12
    score += min(len(extraction.sourceCitations), 5) * 3
    score += min(len(extraction.brandAssetCues), 4) * 4
    score += min(len(site_sections), 5) * 2
    score += 8 if brand_tokens["primaryColor"]["evidence"]["sourceKind"] == "source_backed" else 0
    score += 6 if brand_tokens["typography"]["evidence"]["sourceKind"] == "source_backed" else 0
    score -= min(len(missing_requirements), 5) * 5
    return max(0, min(100, score))


def _readiness_status(brief: SiteBrief, quality_score: int, missing_requirements: list[str]) -> tuple[SiteReadinessStatus, SiteQaStatus]:
    if brief.approvalState != "approved":
        return "blocked", "fail"
    if quality_score >= 85 and not missing_requirements:
        return "ready_to_publish", "pass"
    if quality_score >= 70 and len(missing_requirements) <= 2:
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
    source_sections = ", ".join(section.title for section in brief.recommendedSections[:4]) or "No section titles were approved"
    generated_sections = ", ".join(section["title"] for section in sections[:4])
    entries = [
        {
            "label": "Hero direction",
            "sourceValue": brief.recommendedHero.value or "No hero direction was approved",
            "generatedValue": hero["headline"],
            "status": "matched" if _text(brief.recommendedHero.value) and _text(brief.recommendedHero.value) in hero["headline"] else "inferred",
            "reason": "Hero copy is derived from the approved brief and the extracted positioning cues.",
            "evidence": hero["evidence"],
        },
        {
            "label": "Conversion angle",
            "sourceValue": brief.conversionAngle.value or "No conversion angle was approved",
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
    brief: SiteBrief | None,
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


def _diversity_notes(current: GeneratedSite | None, theme: dict[str, Any], palette_mode: PaletteMode, references: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if current is not None:
        if current.themeKey == theme["themeKey"]:
            notes.append("Theme matches the prior version; review for visual repetition before publish.")
        if current.paletteMode == palette_mode:
            notes.append("Palette matches the prior version; confirm the choice is still source-backed and reviewed.")
    if not notes and references:
        notes.append("Theme and palette are derived from the source cues and remain traceable to extracted evidence.")
    return notes


def _review_state_from(site: GeneratedSite | None, review: dict[str, Any] | None = None) -> ReviewWorkflowState:
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


def _publish_approval_state(site: GeneratedSite | None, review_state: ReviewWorkflowState, missing_requirements: list[str]) -> PublishApprovalState:
    if site is None:
        return "pending"
    if review_state == "blocked" or site.qaStatus == "fail" or missing_requirements:
        return "blocked"
    if site.readinessStatus == "ready_to_publish" and site.qaStatus == "pass":
        return "approved"
    return "pending"


def _review_checklist_pass(review_rubric: list[dict[str, Any]]) -> bool:
    return all(item.get("status") != "fail" for item in review_rubric)


def _screenshot_models(screenshots: list[dict[str, Any]]) -> list[SiteScreenshotMetadata]:
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


def _handoff_record_from_site(site: GeneratedSite, review: dict[str, Any] | None = None) -> SiteHandoffRecord:
    return SiteHandoffRecord(
        id=site.handoffRecordId or site.id,
        siteId=site.id,
        leadId=site.leadId,
        version=site.version,
        status="ready" if site.publishApprovalState == "approved" and site.qaStatus == "pass" and not site.missingRequirements else "blocked",
        sourceAttribution=SiteSourceAttribution.model_validate(site.sourceAttribution) if site.sourceAttribution else SiteSourceAttribution(leadId=site.leadId),
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
        reviewChecklist=[SiteReviewChecklistItem.model_validate(item) for item in (review.get("checklist", []) if review else [])],
        screenshots=_screenshot_models(review.get("screenshots", [])) if review else list(site.screenshotRefs),
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

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None or self._memory_ready:
            return
        self._memory_ready = True
        await database["generated_sites"].create_index("id", unique=True)
        await database["generated_sites"].create_index("leadId")
        await database["generated_sites"].create_index("previewSlug")
        await database["generated_site_versions"].create_index("siteId")
        await database["generated_site_versions"].create_index([("siteId", 1), ("version", -1)])
        await database["site_overrides"].create_index("siteId")
        await database["site_overrides"].create_index([("siteId", 1), ("createdAt", -1)])
        await database["site_overrides"].create_index([("siteId", 1), ("path", 1)])
        await database["site_exports"].create_index("siteId")
        await database["site_exports"].create_index([("siteId", 1), ("createdAt", -1)])
        await database["site_reviews"].create_index("siteId")
        await database["site_reviews"].create_index([("siteId", 1), ("reviewedAt", -1)])
        await database["site_handoffs"].create_index("siteId")
        await database["site_handoffs"].create_index([("siteId", 1), ("createdAt", -1)])

    def get_theme_library(self) -> ThemeLibraryResponse:
        return ThemeLibraryResponse(items=[ThemeVariant.model_validate(theme) for theme in THEME_LIBRARY])

    async def get_site(self, site_id: str) -> GeneratedSite | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                return _site_doc_to_current(doc) if doc else None
        doc = await database["generated_sites"].find_one({"id": site_id})
        return _site_doc_to_current(doc) if doc else None

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
        cursor = database["generated_site_versions"].find({"siteId": site_id}).sort("version", -1)
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

    async def list_review_queue(self, *, limit: int = 25, offset: int = 0) -> SiteReviewQueueResponse:
        await self._maybe_ensure_indexes()
        sites = await self._list_sites(limit=limit, offset=offset)
        items = [_queue_item_from_site(site) for site in sites]
        total = await self._count_sites()
        return SiteReviewQueueResponse(items=items, pagination={"total": total, "limit": limit, "offset": offset})

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
        checklist = list(getattr(request, "checklist", None) or (existing.get("checklist", []) if existing else []))
        screenshots = list(getattr(request, "screenshots", None) or (existing.get("screenshots", []) if existing else []))
        outcome = getattr(request, "outcome", None) or (existing.get("outcome") if existing else site.qaStatus)
        blocked_reason = getattr(request, "blockedReason", None) if getattr(request, "blockedReason", None) is not None else (existing.get("blockedReason") if existing else None)
        notes = getattr(request, "notes", None) if getattr(request, "notes", None) is not None else (existing.get("notes") if existing else None)
        browser_preview_url = getattr(request, "browserPreviewUrl", None) if hasattr(request, "browserPreviewUrl") else (existing.get("browserPreviewUrl") if existing else None)
        review_state = _review_state_from(site, {"outcome": outcome, "blockedReason": blocked_reason})
        source_attribution = _site_source_attribution(
            lead=await lead_repository.get_lead(site_id),
            brief=await lead_repository.get_brief(site_id),
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
            "checklist": [item.model_dump() if hasattr(item, "model_dump") else item for item in checklist],
            "screenshots": [item.model_dump() if hasattr(item, "model_dump") else item for item in screenshots],
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
        await database["site_reviews"].replace_one({"siteId": site_id}, record, upsert=True)
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
                    doc["browserReviewState"] = record["reviewRecordId"] and _review_state_from(site, review) or doc.get("browserReviewState", "not_reviewed")
                    doc["updatedAt"] = now
                return SiteHandoffRecord.model_validate(record)
        await database["site_handoffs"].replace_one({"siteId": site_id}, record, upsert=True)
        await database["generated_sites"].update_one(
            {"id": site_id},
            {"$set": {"handoffRecordId": record["id"], "publishApprovalState": record["publishApprovalState"], "updatedAt": now}},
        )
        return SiteHandoffRecord.model_validate(record)

    async def retry_generation(self, site_id: str) -> GeneratedSite | None:
        site = await self.get_site(site_id)
        if site is None:
            return None
        return await self.generate_site(site_id)

    async def create_override(self, site_id: str, request: SiteOverrideCreateRequest, *, actor: str | None = None) -> SiteOverrideRecord | None:
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
            previousValue=request.previousValue.strip() if request.previousValue else None,
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
                return record
        await database["site_overrides"].insert_one(record.model_dump())
        await database["generated_sites"].update_one(
            {"id": site_id},
            {"$set": {"overrideCount": site.overrideCount + 1, "updatedAt": now}, "$push": {"overrides": record.model_dump()}},
        )
        return record

    async def generate_site(self, site_id: str, request: SiteGenerateRequest | None = None) -> GeneratedSite | None:
        await self._maybe_ensure_indexes()
        lead = await lead_repository.get_lead(site_id)
        if lead is None:
            return None
        brief = await lead_repository.get_brief(site_id)
        if brief is None or brief.approvalState != "approved":
            raise ValueError("brief_not_approved")
        extraction = await lead_repository.get_extraction(site_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("extraction_required")

        current = await self.get_site(site_id)
        next_version = int(current.version if current else 0) + 1
        job_type = "site_generate" if current is None else "site_republish"
        job = await lead_repository.create_job(
            lead_ids=[site_id],
            job_type=job_type,
            status="running",
            progress=15,
            step="Selecting theme and palette",
            metadata={
                "siteId": site_id,
                "leadId": site_id,
                "briefId": brief.id,
                "briefVersion": brief.version,
                "nextVersion": next_version,
            },
        )
        await lead_repository._update_job(job.id, progress=35, step="Building source-safe brand tokens")  # noqa: SLF001

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
                    " ".join(cue.label for cue in extraction.brandAssetCues if cue.assetType == "color"),
                    " ".join(cue.value for cue in extraction.brandAssetCues if cue.assetType == "color"),
                ]
            ),
            extraction,
        )
        refs = _site_refs(brief, extraction)
        brand_tokens = _brand_tokens(
            palette_mode=palette_mode,
            theme=theme,
            brief=brief,
            extraction=extraction,
            refs=refs,
        )
        hero = _hero_variant(brief=brief, extraction=extraction, theme=theme, refs=refs)
        sections = _section_stack(brief=brief, extraction=extraction, refs=refs)
        cta_strategy = _cta_strategy(brief=brief, extraction=extraction, refs=refs)
        missing_requirements = list(dict.fromkeys([*brief.missingRequirements, *extraction.gapItems]))
        if not extraction.brandAssetCues:
            missing_requirements.append("brand_assets_missing")
        if not extraction.sourceCitations:
            missing_requirements.append("source_citations_missing")
        if not brief.recommendedSections:
            missing_requirements.append("section_guidance_missing")
        if not _text(brief.conversionAngle.value):
            missing_requirements.append("cta_strategy_missing")
        missing_requirements = list(dict.fromkeys(missing_requirements))
        quality_score = _quality_score(
            brief=brief,
            extraction=extraction,
            brand_tokens=brand_tokens,
            site_sections=sections,
            missing_requirements=missing_requirements,
        )
        readiness_status, qa_status = _readiness_status(brief, quality_score, missing_requirements)
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
                palette_mode=palette_mode,
                theme=theme,
                brief=brief,
                extraction=extraction,
                refs=refs,
            )
            recomputed_hero = _hero_variant(brief=brief, extraction=extraction, theme=theme, refs=refs)
            recomputed_sections = _section_stack(brief=brief, extraction=extraction, refs=refs)
            recomputed_cta = _cta_strategy(brief=brief, extraction=extraction, refs=refs)

            # Reapply overrides to the recomputed baselines so operator edits persist
            applied_sections = self._apply_overrides(recomputed_sections, overrides)
            applied_hero = self._apply_hero_overrides(recomputed_hero, overrides)
            applied_cta = self._apply_cta_overrides(recomputed_cta, overrides)
            applied_tokens = self._apply_brand_overrides(recomputed_brand_tokens, overrides)
            applied_palette = _text(applied_tokens["paletteMode"]) or palette_mode
            if applied_palette in {"zinc", "light", "colorful"}:
                palette_mode = applied_palette  # type: ignore[assignment]
        quality_score = _quality_score(
            brief=brief,
            extraction=extraction,
            brand_tokens=applied_tokens,
            site_sections=applied_sections,
            missing_requirements=missing_requirements,
        )
        review_rubric = _review_rubric(
            brief=brief,
            extraction=extraction,
            site_sections=applied_sections,
            brand_tokens=applied_tokens,
            palette_mode=palette_mode,
        )
        comparison_entries = _comparison_entries(
            brief=brief,
            theme=theme,
            palette_mode=palette_mode,
            hero=applied_hero,
            sections=applied_sections,
            cta_strategy=applied_cta,
            brand_tokens=applied_tokens,
        )
        version_id = uuid4().hex
        now = _now()
        version_doc = {
            "id": version_id,
            "siteId": site_id,
            "leadId": site_id,
            "generationJobId": job.id,
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
            "qualityScore": quality_score,
            "readinessStatus": readiness_status,
            "qaStatus": qa_status,
            "reviewRubric": review_rubric,
            "comparisonEntries": comparison_entries,
            "sourceTraceability": refs[:8],
            "missingRequirements": missing_requirements,
            "sourceAttribution": _site_source_attribution(lead=lead, brief=brief, extraction=extraction, theme=theme, palette_mode=palette_mode),
            "browserReviewState": _review_state_from(current),
            "publishApprovalState": _publish_approval_state(current, _review_state_from(current), missing_requirements),
            "screenshotRefs": list(getattr(current, "screenshotRefs", [])) if current else [],
            "latestReviewId": current.latestReviewId if current else None,
            "handoffRecordId": current.handoffRecordId if current else None,
            "diversityNotes": _diversity_notes(current, theme, palette_mode, refs),
            "previewSlug": site_id,
            "previewUrl": f"/sites/{site_id}",
            "overrideCount": len(overrides),
            "createdAt": now,
            "updatedAt": now,
            "publishedAt": now if readiness_status == "published" else None,
        }
        site_doc = {
            "id": site_id,
            "leadId": site_id,
            "generationJobId": job.id,
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
            "qualityScore": quality_score,
            "readinessStatus": readiness_status,
            "qaStatus": qa_status,
            "reviewRubric": review_rubric,
            "comparisonEntries": comparison_entries,
            "sourceTraceability": refs[:8],
            "missingRequirements": missing_requirements,
            "sourceAttribution": _site_source_attribution(lead=lead, brief=brief, extraction=extraction, theme=theme, palette_mode=palette_mode),
            "browserReviewState": _review_state_from(current),
            "publishApprovalState": _publish_approval_state(current, _review_state_from(current), missing_requirements),
            "screenshotRefs": list(getattr(current, "screenshotRefs", [])) if current else [],
            "latestReviewId": current.latestReviewId if current else None,
            "handoffRecordId": current.handoffRecordId if current else None,
            "diversityNotes": _diversity_notes(current, theme, palette_mode, refs),
            "previewSlug": site_id,
            "previewUrl": f"/sites/{site_id}",
            "overrideCount": len(overrides),
            "overrides": overrides,
            "exportMetadata": None,
            "createdAt": current.createdAt if current else now,
            "updatedAt": now,
            "publishedAt": now if readiness_status == "published" else None,
        }
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._sites[site_id] = site_doc
                self._versions.setdefault(site_id, []).append(version_doc)
                self._overrides.setdefault(site_id, overrides)
                self._reviews.setdefault(site_id, self._reviews.get(site_id, {}))
                await lead_repository._update_job(  # noqa: SLF001
                    job.id,
                    status="completed",
                    progress=100,
                    step="Preview generated" if current is None else "Preview republished",
                    finished=True,
                    lead_ids=[site_id],
                    metadata={
                        "siteId": site_id,
                        "leadId": site_id,
                        "briefId": brief.id,
                        "briefVersion": brief.version,
                        "version": next_version,
                    },
                )
                return _site_doc_to_current(site_doc)

        await database["generated_site_versions"].insert_one(version_doc)
        if current is None:
            await database["generated_sites"].insert_one(site_doc)
        else:
            await database["generated_sites"].replace_one({"id": site_id}, site_doc, upsert=True)
        completed_step = "Preview generated" if current is None else "Preview republished"
        await lead_repository._update_job(  # noqa: SLF001
            job.id,
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
            },
        )
        return _site_doc_to_current(site_doc)

    async def republish_site(self, site_id: str) -> GeneratedSite | None:
        return await self.generate_site(site_id)

    async def add_export_metadata(self, site_id: str, export_metadata: SiteExportMetadata) -> SiteExportMetadata | None:
        await self._maybe_ensure_indexes()
        site = await self.get_site(site_id)
        if site is None:
            return None
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._sites.get(site_id)
                if doc is not None:
                    doc["exportMetadata"] = export_metadata.model_dump()
                    doc["updatedAt"] = _now()
                self._exports.setdefault(site_id, []).append(export_metadata.model_dump())
                return export_metadata
        await database["site_exports"].insert_one({"siteId": site_id, **export_metadata.model_dump()})
        await database["generated_sites"].update_one(
            {"id": site_id},
            {"$set": {"exportMetadata": export_metadata.model_dump(), "updatedAt": _now()}},
        )
        return export_metadata

    async def _get_review_doc(self, site_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return self._reviews.get(site_id)
        return await database["site_reviews"].find_one({"siteId": site_id})

    async def _apply_review_to_site(self, site_id: str, review_doc: dict[str, Any]) -> None:
        now = _now()
        database = get_database()
        review_state = _review_state_from(None, review_doc)
        publish_state = "blocked" if review_doc.get("blockedReason") or review_doc.get("outcome") == "fail" else ("approved" if review_doc.get("outcome") == "pass" else "pending")
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
            {"$set": {"browserReviewState": review_state, "publishApprovalState": publish_state, "latestReviewId": review_doc.get("id"), "screenshotRefs": review_doc.get("screenshots", []), "updatedAt": now}},
        )

    def _handoff_doc_for_site(self, site: GeneratedSite, review_doc: dict[str, Any] | None) -> dict[str, Any]:
        review_state = _review_state_from(site, review_doc)
        publish_state = _publish_approval_state(site, review_state, list(site.missingRequirements))
        review_checklist = list(review_doc.get("checklist", [])) if review_doc else []
        screenshots = list(review_doc.get("screenshots", [])) if review_doc else list(site.screenshotRefs)
        status = "ready" if publish_state == "approved" and review_state == "approved" and not site.missingRequirements else "blocked"
        return {
            "id": site.handoffRecordId or uuid4().hex,
            "siteId": site.id,
            "leadId": site.leadId,
            "version": site.version,
            "status": status,
            "sourceAttribution": site.sourceAttribution.model_dump() if hasattr(site.sourceAttribution, "model_dump") else site.sourceAttribution,
            "previewSlug": site.previewSlug,
            "previewUrl": site.previewUrl,
            "themeKey": site.themeKey,
            "paletteMode": site.paletteMode,
            "qualityScore": site.qualityScore,
            "readinessStatus": site.readinessStatus,
            "qaStatus": site.qaStatus,
            "publishApprovalState": publish_state,
            "reviewRecordId": review_doc.get("id") if review_doc else site.latestReviewId,
            "reviewOutcome": review_doc.get("outcome") if review_doc else None,
            "reviewChecklist": review_checklist,
            "screenshots": screenshots,
            "sourceTraceability": list(site.sourceTraceability),
            "missingRequirements": list(site.missingRequirements),
            "exportMetadata": site.exportMetadata.model_dump() if site.exportMetadata else None,
            "createdAt": site.createdAt,
            "updatedAt": _now(),
        }

    async def _list_sites(self, *, limit: int, offset: int) -> list[GeneratedSite]:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = list(self._sites.values())
                docs.sort(key=lambda item: item.get("updatedAt", _now()), reverse=True)
                return [_site_doc_to_current(doc) for doc in docs[offset : offset + limit]]
        cursor = database["generated_sites"].find({}).sort("updatedAt", -1).skip(offset).limit(limit)
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
                return [dict(item) for item in self._overrides.get(site_id, []) if item.get("status", "active") == "active"]
        cursor = database["site_overrides"].find({"siteId": site_id, "status": "active"}).sort("createdAt", 1)
        docs = await cursor.to_list(length=100)
        return [dict(doc) for doc in docs]

    def _apply_overrides(self, sections: list[dict[str, Any]], overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                match = re.match(r"sections\.(\d+)\.(title|headline|body|ctaLabel|eyebrow)", path)
                if match:
                    index = int(match.group(1))
                    field = match.group(2)
                    if 0 <= index < len(updated_sections):
                        updated_sections[index][field] = value
            elif path == "cta.primary.label" and updated_sections:
                updated_sections[-1]["ctaLabel"] = value
        return updated_sections

    def _apply_hero_overrides(self, hero: dict[str, Any], overrides: list[dict[str, Any]]) -> dict[str, Any]:
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

    def _apply_cta_overrides(self, cta_strategy: dict[str, Any], overrides: list[dict[str, Any]]) -> dict[str, Any]:
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

    def _apply_brand_overrides(self, brand_tokens: dict[str, Any], overrides: list[dict[str, Any]]) -> dict[str, Any]:
        updated = {key: (dict(value) if isinstance(value, dict) else value) for key, value in brand_tokens.items()}
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
