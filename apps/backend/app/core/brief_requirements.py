"""Deterministic safety gates for evidence-aware master briefs."""

from __future__ import annotations

from app.schemas.brief import MasterBrief


INTENTIONAL_FALLBACK_REQUIREMENTS = frozenset(
    {
        "approved_hero_or_project_images",
        "approved_proof_evidence",
        "approved_logo_or_wordmark",
    }
)


def fallback_requirements(blockers: list[str]) -> list[str]:
    """Return requirements that generation can satisfy with safe fallbacks."""
    return [item for item in blockers if item in INTENTIONAL_FALLBACK_REQUIREMENTS]


def _has_images(brief: MasterBrief) -> bool:
    assets = brief.brandAssets
    return bool(assets.imageUrls or assets.imageInventory)


def _has_proof_evidence(brief: MasterBrief) -> bool:
    return bool(getattr(brief, "extractedContent", {}).get("testimonials"))


def validate_master_brief_requirements(brief: MasterBrief) -> list[str]:
    """Return hard blockers; this function never trusts prose-only claims."""
    missing = list(dict.fromkeys(brief.missingRequirements))
    image_required = any(
        token
        in f"{section.purpose} {section.suggestedApproach} {section.contentSummary}".lower()
        for section in brief.sections
        for token in (
            "gallery",
            "carousel",
            "full-bleed image",
            "photo",
            "hero image",
            "before/after",
        )
    ) or any(
        token in brief.creativeDirection.heroTreatment.lower()
        for token in ("image", "photo", "video")
    )
    if image_required and not _has_images(brief):
        missing.append("approved_hero_or_project_images")
    proof_required = any(
        token
        in f"{section.purpose} {section.suggestedApproach} {section.contentSummary}".lower()
        for section in brief.sections
        for token in ("testimonial", "review", "rating", "social proof", "quote")
    )
    if proof_required and not _has_proof_evidence(brief):
        missing.append("approved_proof_evidence")
    if not brief.brandAssets.logoUrl and not brief.brandAssets.logoVariants:
        missing.append("approved_logo_or_wordmark")
    return list(dict.fromkeys(missing))


def brief_is_approvable(brief: MasterBrief) -> bool:
    return not validate_master_brief_requirements(brief)
