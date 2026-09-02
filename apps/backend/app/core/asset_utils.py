"""
Utility functions for brand asset URL handling.

Provides centralized logic for selecting best asset URLs (preferring S3 cached
versions over original source URLs) with validation and telemetry.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

if TYPE_CHECKING:
    from app.schemas.extraction import BrandAssetCue

logger = logging.getLogger(__name__)


def validate_asset_url(url: str | None) -> str | None:
    """
    Validate and return asset URL, or None if invalid.

    Args:
        url: URL string to validate

    Returns:
        Validated URL or None if invalid/empty
    """
    if not url or not url.strip():
        return None

    url = url.strip()

    # Basic URL validation - must have protocol
    if not url.startswith(("http://", "https://")):
        return None

    # Don't pass localhost/dev URLs to LLM
    if "localhost" in url or "127.0.0.1" in url:
        logger.warning(f"Filtering out localhost URL: {url[:50]}...")
        return None

    return url


def _cached_render_url(value: object) -> str | None:
    """Resolve a cached asset reference to a URL safe for generated markup."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value.startswith("data:"):
        return value
    if value.startswith("/api/internal/assets/"):
        base = (os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")
        return f"{base}{value}" if base else value
    if value.startswith(("https://", "http://")):
        return value.replace("http://", "https://", 1) if value.startswith("http://") else value
    if value.startswith(("local://", "s3://", "gs://")):
        try:
            from app.core.asset_urls import get_asset_signed_url

            signed = get_asset_signed_url(value)
            if signed.startswith("/"):
                base = (os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")
                return f"{base}{signed}" if base else signed
            return signed if signed.startswith(("https://", "http://")) else None
        except Exception as exc:
            logger.warning("Unable to sign cached asset reference: %s", exc)
    return None


def get_cached_asset_url(cue: BrandAssetCue | dict[str, Any]) -> str | None:
    """Return only a cached asset URL; never fall back to the source website."""
    if isinstance(cue, dict):
        cached = cue.get("cachedUrl") or cue.get("cachedUri")
    else:
        cached = getattr(cue, "cachedUrl", None) or getattr(cue, "cachedUri", None)
    return _cached_render_url(cached)


def get_cached_asset_urls(
    cues: Sequence[BrandAssetCue | dict[str, Any]], max_count: int = 5
) -> list[str]:
    urls: list[str] = []
    for cue in cues:
        url = get_cached_asset_url(cue)
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= max_count:
            break
    return urls


def get_best_asset_url(cue: BrandAssetCue | dict[str, Any]) -> str | None:
    """
    Get the best available URL for an asset cue.

    Prefers cachedUri (S3) over sourceUrl (original website).
    Validates the URL before returning.

    Args:
        cue: BrandAssetCue model or dict with cachedUri/sourceUrl fields

    Returns:
        Best available valid URL, or None if no valid URL available
    """
    if isinstance(cue, dict):
        cached = cue.get("cachedUrl") or cue.get("cachedUri")
        asset, value, page, legacy = cue.get("assetUrl"), cue.get("value"), cue.get("pageUrl"), cue.get("sourceUrl")
    else:
        cached = getattr(cue, "cachedUrl", None) or cue.cachedUri
        asset, value, page, legacy = getattr(cue, "assetUrl", None), cue.value, getattr(cue, "pageUrl", None), cue.sourceUrl

    cached_render_url = get_cached_asset_url(cue)
    if cached_render_url:
        return cached_render_url

    # Prefer the cached URL when it is valid, then fall back to the source URL.
    # A malformed cached/relative value must not prevent a valid source asset
    # from being selected.
    if validate_asset_url(cached):
        return validate_asset_url(cached)
    for candidate in (asset, value):
        resolved = _resolve_asset_candidate(candidate, page)
        if resolved:
            return resolved
    # sourceUrl is legacy page provenance, never an asset merely because it is
    # absolute. Only accept it when its path demonstrably identifies an asset.
    return _resolve_asset_candidate(legacy, None, require_asset_path=True)


def _resolve_asset_candidate(value: str | None, page_url: str | None, require_asset_path: bool = False) -> str | None:
    if not value:
        return None
    resolved = urljoin(page_url, value) if page_url and not value.startswith(("http://", "https://")) else value
    resolved = validate_asset_url(resolved)
    if not resolved:
        return None
    path = urlparse(resolved).path.lower()
    asset_path = any(path.endswith(ext) for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".woff", ".woff2", ".ttf", ".otf"))
    if require_asset_path and not asset_path:
        return None
    # A root/homepage URL cannot be an image asset even when stale data labels it so.
    if not path or path == "/":
        return None
    return resolved


def get_best_asset_urls(
    cues: Sequence[BrandAssetCue | dict[str, Any]], max_count: int = 5
) -> list[str]:
    """
    Get best URLs for a list of asset cues, filtering out invalid ones.

    Args:
        cues: List of BrandAssetCue models or dicts
        max_count: Maximum number of URLs to return

    Returns:
        List of valid URLs (may be shorter than max_count if some are invalid)
    """
    urls = []
    for cue in cues[:max_count]:
        url = get_best_asset_url(cue)
        if url:
            urls.append(url)
    return urls


def log_asset_cache_stats(
    cues: Sequence[BrandAssetCue | dict[str, Any]],
    asset_type: str,
    lead_id: str | None = None,
) -> dict[str, Any]:
    """
    Log cache hit rates for asset URLs and return stats.

    Args:
        cues: List of BrandAssetCue models or dicts
        asset_type: Type of asset for logging (e.g., "logo", "image")
        lead_id: Optional lead ID for context in logs

    Returns:
        Dict with cache statistics
    """
    total = len(cues)
    if total == 0:
        return {
            "total": 0,
            "cached": 0,
            "source_only": 0,
            "invalid": 0,
            "hit_rate": 0.0,
        }

    cached = 0
    source_only = 0
    invalid = 0

    for cue in cues:
        if isinstance(cue, dict):
            cached_uri = cue.get("cachedUri")
            source_url = cue.get("sourceUrl")
        else:
            cached_uri = cue.cachedUri
            source_url = cue.sourceUrl

        if get_cached_asset_url(cue):
            cached += 1
        elif validate_asset_url(source_url):
            source_only += 1
        else:
            invalid += 1

    hit_rate = (cached / total * 100) if total > 0 else 0.0

    context = f" for lead {lead_id}" if lead_id else ""
    logger.info(
        f"Asset cache stats{context} - {asset_type}: "
        f"{cached}/{total} cached ({hit_rate:.1f}% hit rate), "
        f"{source_only} source-only, {invalid} invalid"
    )

    return {
        "total": total,
        "cached": cached,
        "source_only": source_only,
        "invalid": invalid,
        "hit_rate": hit_rate,
    }
