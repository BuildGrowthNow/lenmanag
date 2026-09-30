from __future__ import annotations

import hashlib
import json
import logging
from io import BytesIO
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat, ImageOps
from app.core.config import get_settings
from app.core.screenshot_analyzer import get_screenshot_analyzer
from app.schemas.site import GeneratedSite

logger = logging.getLogger(__name__)

RENDERED_VARIANT_MIN_DIFFERENCE = 0.12
RENDERED_VARIANT_MIN_STRUCTURAL_DIFFERENCE = 0.18


def rendered_visual_difference(screenshot_a: bytes, screenshot_b: bytes) -> float:
    """Return a perceptual pixel difference from 0.0 (same) to 1.0."""
    first = Image.open(BytesIO(screenshot_a)).convert("RGB")
    second = Image.open(BytesIO(screenshot_b)).convert("RGB")
    size = (96, 96)
    canvas_a = first.resize(size)
    canvas_b = second.resize(size)
    difference = ImageChops.difference(canvas_a, canvas_b)
    mean = sum(ImageStat.Stat(difference).mean) / (3 * 255)
    return round(min(1.0, max(0.0, mean)), 4)


def rendered_structural_difference(screenshot_a: bytes, screenshot_b: bytes) -> float:
    """Compare edge/layout evidence while discounting palette-only changes."""
    first = Image.open(BytesIO(screenshot_a)).convert("RGB").resize((192, 192))
    second = Image.open(BytesIO(screenshot_b)).convert("RGB").resize((192, 192))
    first_edges = ImageOps.grayscale(first).filter(ImageFilter.FIND_EDGES)
    second_edges = ImageOps.grayscale(second).filter(ImageFilter.FIND_EDGES)
    difference = ImageChops.difference(first_edges, second_edges)
    mean = ImageStat.Stat(difference).mean[0] / 255
    return round(min(1.0, max(0.0, mean)), 4)


def rendered_variant_difference_score(screenshot_a: bytes, screenshot_b: bytes) -> dict[str, Any]:
    """Return both palette and structural evidence for a variant gate."""
    color = rendered_visual_difference(screenshot_a, screenshot_b)
    structural = rendered_structural_difference(screenshot_a, screenshot_b)
    composite = round((structural * 0.8) + (color * 0.2), 4)
    return {
        "difference": color,
        "structuralDifference": structural,
        "compositeDifference": composite,
        "paletteOnly": structural < RENDERED_VARIANT_MIN_STRUCTURAL_DIFFERENCE and color >= RENDERED_VARIANT_MIN_DIFFERENCE,
        "distinct": structural >= RENDERED_VARIANT_MIN_STRUCTURAL_DIFFERENCE,
    }


class ScreenshotComparator:
    """Handles screenshot capture, comparison, and layout duplicate detection."""

    def compute_layout_hash(self, site: GeneratedSite) -> str:
        """
        Hash section stack, hero variant, and theme key for duplicate detection.
        Returns a SHA-256 hash string.
        """
        data = {
            "themeKey": site.themeKey,
            "paletteMode": site.paletteMode,
            "heroLayout": site.heroVariant.layout,
            "sectionCount": len(site.sectionStack),
            "sectionTitles": [s.title for s in site.sectionStack],
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def detect_duplicate_layout(
        self, site_a: GeneratedSite, site_b: GeneratedSite
    ) -> float:
        """
        Returns similarity score (0-1) between two sites based on layout.
        1.0 = identical layout, 0.0 = completely different.
        """
        hash_a = self.compute_layout_hash(site_a)
        hash_b = self.compute_layout_hash(site_b)
        # Simple hash comparison for now
        # Can be enhanced with weighted similarity scoring
        return 1.0 if hash_a == hash_b else 0.0

    def compare_rendered_screenshots(
        self,
        screenshot_a: bytes,
        screenshot_b: bytes,
        *,
        minimum_difference: float = RENDERED_VARIANT_MIN_DIFFERENCE,
    ) -> dict[str, Any]:
        """Enforce a final rendered-difference gate between variants."""
        evidence = rendered_variant_difference_score(screenshot_a, screenshot_b)
        return {
            **evidence,
            "minimumDifference": minimum_difference,
            "minimumStructuralDifference": RENDERED_VARIANT_MIN_STRUCTURAL_DIFFERENCE,
        }

    async def compare_layout_screenshot(
        self,
        site_id: str,
        preview_url: str,
        base_url: str | None = None,
        section_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Capture a screenshot of the preview and return QA metrics.

        The base URL for the preview server is resolved in this order:
        1. Explicit ``base_url`` argument if provided.
        2. ``settings.preview_base_url`` from configuration.
        3. Fallback to ``http://localhost:3000`` and, if that fails,
           a final attempt to ``http://localhost:3003`` for local dev
           scenarios where port 3000 is already in use.
        """
        try:
            settings = get_settings()
            analyzer = get_screenshot_analyzer()

            # Resolve an initial base URL from argument or settings.
            effective_base_url = base_url or getattr(
                settings, "preview_base_url", "http://localhost:3000"
            )

            async def _capture_with_base(url: str) -> dict[str, Any]:
                return await analyzer.capture_screenshots(
                    site_id=site_id,
                    preview_url=preview_url,
                    base_url=url,
                )

            # First attempt: configured/default base URL.
            try:
                screenshots = await _capture_with_base(effective_base_url)
            except Exception as e:
                logger.warning(
                    "Screenshot capture failed for %s at %s: %s",
                    site_id,
                    effective_base_url,
                    e,
                )
                # Local dev fallback: try common alternate Next.js port 3003
                if effective_base_url.rstrip("/").endswith(":3000"):
                    alt_base = (
                        effective_base_url.rstrip("/").rsplit(":", 1)[0] + ":3003"
                    )
                    logger.info(
                        "Retrying screenshot capture for %s at alternate base_url=%s",
                        site_id,
                        alt_base,
                    )
                    screenshots = await _capture_with_base(alt_base)
                else:
                    raise

            # Perform QA analysis on desktop screenshot.
            # If the caller did not provide real section names, fall back to a
            # small set of generic labels for backward compatibility.
            effective_section_names = (
                section_names
                if section_names
                else [
                    "Hero",
                    "Services",
                    "Proof",
                    "Features",
                    "CTA",
                ]
            )

            qa_result: dict[str, Any]
            try:
                settings = get_settings()
                qa_result = await analyzer.perform_qa_analysis(
                    site_id=site_id,
                    desktop_screenshot=screenshots["desktopScreenshot"],
                    extraction_summary="Generated preview page",
                    section_stack=effective_section_names,
                    quality_threshold=settings.visual_redesign_quality_threshold,
                )
            except Exception as e:  # noqa: BLE001
                # Treat QA as best-effort: if Gemini or analysis fails, still
                # return successful screenshot capture so the pipeline can
                # attach screenshotRefs and rely on existing quality scoring.
                logger.error("QA analysis failed for %s: %s", site_id, e)
                qa_result = {
                    "qualityScore": None,
                    "available": False,
                    "sectionScores": [],
                    "rawCritique": f"QA analysis failed: {e}",
                    "readinessAssessment": "needs_refinement",
                    "passThreshold": False,
                }

            return {
                "success": True,
                "desktopScreenshotUrl": screenshots["desktopUrl"],
                "mobileScreenshotUrl": screenshots["mobileUrl"],
                "layoutHash": screenshots["layoutHash"],
                "qualityScore": qa_result.get("qualityScore", 50),
                "qualityScoreSource": "visual" if qa_result.get("available", False) else "fallback",
                "qaAvailable": bool(qa_result.get("available", False)),
                "sectionScores": qa_result.get("sectionScores", []),
                "rawCritique": qa_result.get("rawCritique", ""),
                "readinessAssessment": qa_result.get(
                    "readinessAssessment", "needs_refinement"
                ),
                "passThreshold": qa_result.get("passThreshold", False),
                "capturedAt": screenshots["capturedAt"],
            }
        except Exception as e:
            logger.error(f"Screenshot comparison failed for {site_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "qualityScore": 0,
                "sectionScores": [],
                "rawCritique": f"Screenshot capture failed: {e}",
                "readinessAssessment": "blocked",
                "passThreshold": False,
            }
