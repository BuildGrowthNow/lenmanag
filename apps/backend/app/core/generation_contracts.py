"""Fail-closed contracts shared by generation preflight and provider execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


IMAGE_LED = "image_led"
TYPOGRAPHY_ONLY = "typography_only"


@dataclass(frozen=True)
class GenerationBlock:
    rule_id: str
    message: str
    stage: str = "preflight"


@dataclass
class GenerationPreflight:
    hero_mode: str
    approved_assets: list[str] = field(default_factory=list)
    rejected_assets: list[dict[str, Any]] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    blocks: list[GenerationBlock] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return not self.blocks


def _cached_https(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value.startswith(("https://", "/api/internal/assets/")) else None


def generation_preflight(brief: Any, *, asset_download_enabled: bool) -> GenerationPreflight:
    """Make an image contract explicit before any provider request is made."""
    assets = getattr(brief, "brandAssets", None)
    inventory = list(getattr(assets, "imageInventory", None) or [])
    urls = list(getattr(assets, "imageUrls", None) or [])
    approved = [url for item in inventory if isinstance(item, dict) and item.get("approved") for url in [_cached_https(item.get("url"))] if url]
    approved.extend(url for url in (_cached_https(item) for item in urls) if url and url not in approved)
    discovered = [item for item in inventory if isinstance(item, dict) and (item.get("sourceUrl") or item.get("url"))]
    rejected = [item for item in inventory if isinstance(item, dict) and not _cached_https(item.get("url"))]
    mode = str(getattr(brief, "heroMode", "") or "").strip().lower()
    if mode not in {IMAGE_LED, TYPOGRAPHY_ONLY}:
        # Existing briefs without a declared choice are safe only when they have
        # approved media. Otherwise they must opt into the explicit fallback.
        mode = IMAGE_LED if approved else TYPOGRAPHY_ONLY
    missing = list(getattr(brief, "missingRequirements", None) or [])
    blocks: list[GenerationBlock] = []
    if discovered and not asset_download_enabled:
        blocks.append(GenerationBlock("assets.downloader_disabled", "Source assets were discovered but asset downloading is disabled."))
    if mode == IMAGE_LED and not approved:
        blocks.append(GenerationBlock("hero.approved_media_required", "Image-led hero requires at least one approved cached HTTPS asset."))
    return GenerationPreflight(mode, approved, rejected, missing, blocks)
