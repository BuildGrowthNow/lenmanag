from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.config import get_settings
from app.core.screenshot_analyzer import get_screenshot_analyzer
from app.schemas.site import GeneratedSite

logger = logging.getLogger(__name__)


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
                    "qualityScore": 0,
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
