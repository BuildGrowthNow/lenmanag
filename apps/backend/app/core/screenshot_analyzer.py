from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from playwright.async_api import async_playwright

from app.core.llm import get_llm_client

logger = logging.getLogger(__name__)


class ScreenshotAnalyzer:
    """
    Captures screenshots of generated preview pages and performs visual QA using Gemini Vision.
    Produces structured quality scores and section-level critiques.
    """

    # Premium component IDs referenced in visual redesign briefs
    AVAILABLE_COMPONENTS = [
        {
            "id": "hero-split-editorial",
            "name": "Split Editorial Hero",
            "description": "High-contrast editorial hero with split layout",
        },
        {
            "id": "hero-stacked-panel",
            "name": "Stacked Panel Hero",
            "description": "Balanced stacked hero with confident CTA",
        },
        {
            "id": "hero-media-led",
            "name": "Media-Led Hero",
            "description": "Image-first hero with expressive palette",
        },
        {
            "id": "services-grid",
            "name": "Services Grid",
            "description": "Dynamic grid layout for service offerings",
        },
        {
            "id": "services-bento",
            "name": "Services Bento",
            "description": "Bento-style service grid with varied item sizes",
        },
        {
            "id": "proof-carousel",
            "name": "Proof Carousel",
            "description": "Testimonial/proof carousel with movement",
        },
        {
            "id": "proof-masonry",
            "name": "Proof Masonry",
            "description": "Masonry layout for proof points and highlights",
        },
        {
            "id": "gallery-masonry",
            "name": "Gallery Masonry",
            "description": "Masonry work/portfolio gallery",
        },
        {
            "id": "gallery-grid",
            "name": "Gallery Grid",
            "description": "Uniform grid gallery layout",
        },
        {
            "id": "timeline-vertical",
            "name": "Timeline Vertical",
            "description": "Vertical process timeline",
        },
        {
            "id": "timeline-horizontal",
            "name": "Timeline Horizontal",
            "description": "Horizontal process timeline",
        },
        {
            "id": "cta-banner",
            "name": "CTA Banner",
            "description": "Full-width conversion-focused CTA panel",
        },
        {
            "id": "cta-sticky",
            "name": "Sticky CTA",
            "description": "Sticky footer CTA bar",
        },
        {
            "id": "editorial-feature",
            "name": "Editorial Feature",
            "description": "Large editorial content feature block",
        },
        {
            "id": "editorial-frame",
            "name": "Editorial Frame",
            "description": "Spacious editorial frame with high contrast",
        },
    ]

    async def capture_screenshots(
        self,
        site_id: str,
        preview_url: str,
        base_url: str = "http://localhost:3000",
    ) -> dict[str, Any]:
        """
        Capture full-page desktop and mobile screenshots of the preview page.

        Args:
            site_id: ID of the generated site
            preview_url: Relative URL of the preview (e.g., "/sites/site-123")
            base_url: Base URL of the preview server

        Returns:
            Dictionary with:
            - desktopScreenshot: bytes (PNG)
            - mobileScreenshot: bytes (PNG)
            - desktopUrl: storage reference
            - mobileUrl: storage reference
            - layoutHash: stable hash of layout
            - capturedAt: timestamp
        """
        full_url = f"{base_url}{preview_url}"
        screenshots = {
            "desktopScreenshot": None,
            "mobileScreenshot": None,
            "desktopUrl": "",
            "mobileUrl": "",
            "layoutHash": "",
            "capturedAt": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                # Desktop screenshot (1440x1200)
                desktop_page = await browser.new_page(
                    viewport={"width": 1440, "height": 1200},
                    device_scale_factor=1,
                )
                await desktop_page.goto(full_url, wait_until="networkidle")
                desktop_screenshot = await desktop_page.screenshot(
                    path=None, full_page=True, type="png"
                )
                screenshots["desktopScreenshot"] = desktop_screenshot
                screenshots["desktopUrl"] = f"screenshots/{site_id}/desktop.png"
                await desktop_page.close()

                # Mobile screenshot (390x844)
                mobile_page = await browser.new_page(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=1,
                )
                await mobile_page.goto(full_url, wait_until="networkidle")
                mobile_screenshot = await mobile_page.screenshot(
                    path=None, full_page=True, type="png"
                )
                screenshots["mobileScreenshot"] = mobile_screenshot
                screenshots["mobileUrl"] = f"screenshots/{site_id}/mobile.png"
                await mobile_page.close()

                # Compute layout hash
                layout_data = {
                    "siteId": site_id,
                    "capturedAt": screenshots["capturedAt"],
                    "desktopSize": desktop_screenshot.__sizeof__(),
                    "mobileSize": mobile_screenshot.__sizeof__(),
                }
                screenshots["layoutHash"] = hashlib.sha256(
                    json.dumps(layout_data, sort_keys=True).encode()
                ).hexdigest()

                await browser.close()
        except Exception as e:
            logger.error(f"Screenshot capture failed for {site_id}: {e}")
            raise

        return screenshots

    async def perform_qa_analysis(
        self,
        site_id: str,
        desktop_screenshot: bytes,
        extraction_summary: str,
        section_stack: list[str],
        quality_threshold: int = 75,
    ) -> dict[str, Any]:
        """
        Analyze screenshot using Gemini Vision for visual QA.

        Args:
            site_id: ID of the generated site
            desktop_screenshot: PNG screenshot bytes
            extraction_summary: Text summary of extracted site
            section_stack: List of section titles in order
            quality_threshold: Target quality score (0-100)

        Returns:
            Dictionary with:
            - qualityScore: overall score (0-100)
            - sectionScores: array of {sectionId, score, critique, recommendation}
            - rawCritique: full Gemini response
            - passThreshold: whether qualityScore >= quality_threshold
        """
        try:
            client = get_llm_client()

            # Build QA prompt targeting strict premium design criteria
            qa_prompt = f"""You are a STRICT premium web design QA specialist. Analyze this screenshot with CRITICAL evaluation.

Site ID: {site_id}
Sections: {", ".join(section_stack[:8])}

PREMIUM DESIGN CRITERIA (each section must meet these):
1. ADVANCED LAYOUT: Uses bento grids, masonry, carousels, timelines, or split layouts (NOT simple 2-column)
2. VISUAL HIERARCHY: Clear hierarchy with varied typography (size, weight, color)
3. SPACING: Generous padding/margins, breathing room between sections
4. IMAGES: High-quality images with proper aspect ratios, not placeholders
5. BRAND PERSONALITY: Reflects source website's colors, typography, and style
6. CONTRAST: Excellent readability with proper color contrast
7. MOTION: Subtle animations or transitions (if visible)

AUTOMATIC FAILURE CRITERIA (score 0-30 if ANY are true):
- Repeated sections or duplicate content
- All sections using the same basic layout
- Missing images or broken image placeholders
- Generic placeholder styling with no brand personality
- Poor contrast or readability issues
- No premium component layouts (all sections look the same)

SCORING RULES:
- 90-100: Premium design with advanced layouts, excellent hierarchy, brand personality
- 75-89: Good design with some premium elements, mostly correct hierarchy
- 50-74: Basic design with minimal premium elements, needs refinement
- 0-49: Broken design, repeated sections, no premium components, or placeholder styling

Return ONLY valid JSON, no markdown or additional text:
{{
  "qualityScore": <integer 0-100, STRICT scoring>,
  "hasRepeatedSections": <boolean>,
  "usesBasicLayoutsOnly": <boolean>,
  "hasPremiumComponents": <boolean>,
  "missingImages": <boolean>,
  "sectionScores": [
    {{
      "sectionTitle": <string>,
      "score": <integer 0-100>,
      "layoutType": <"advanced" | "basic" | "repeated">,
      "critique": <string, 1-2 sentences>,
      "recommendation": <string or null>
    }}
  ],
  "overallCritique": <string with main strengths and critical issues>,
  "readinessAssessment": <"production_ready" | "needs_refinement" | "blocked">
}}"""

            qa_response = await client.analyze_image(
                prompt=qa_prompt,
                image_data=desktop_screenshot,
                image_mime_type="image/png",
                temperature=0.5,
                max_tokens=1500,
            )

            # Parse QA response
            try:
                qa_result = client.extract_json_from_response(qa_response)
            except ValueError as e:
                logger.error(f"Failed to parse QA response for {site_id}: {e}")
                qa_result = {
                    "qualityScore": 30,  # Conservative default when response is unparseable
                    "sectionScores": [],
                    "overallCritique": qa_response[:500],
                    "readinessAssessment": "needs_refinement",
                    "hasRepeatedSections": False,
                    "usesBasicLayoutsOnly": True,
                    "hasPremiumComponents": False,
                    "missingImages": True,
                }

            return {
                "qualityScore": qa_result.get("qualityScore", 50),
                "sectionScores": qa_result.get("sectionScores", []),
                "rawCritique": qa_response,
                "passThreshold": qa_result.get("qualityScore", 0) >= quality_threshold,
                "readinessAssessment": qa_result.get(
                    "readinessAssessment", "needs_refinement"
                ),
            }
        except Exception as e:
            logger.error(f"QA analysis failed for {site_id}: {e}")
            raise

    async def generate_improvement_brief(
        self,
        site_id: str,
        extraction_summary: str,
        section_stack: list[str],
        qa_critique: str,
        brand_summary: str,
    ) -> dict[str, Any]:
        """
        Generate an improvement brief when quality score is below threshold.
        Uses Gemini to recommend section-level refinements.

        Args:
            site_id: ID of the generated site
            extraction_summary: Text summary of extracted site
            section_stack: List of section titles
            qa_critique: Previous QA critique from vision analysis
            brand_summary: Summary of brand tokens

        Returns:
            Dictionary with improvement recommendations per section
        """
        try:
            client = get_llm_client()

            improvement_prompt = f"""You are a design refinement specialist. Based on the visual QA critique below, 
recommend targeted improvements to increase quality from below 75 to at least 85.

Site ID: {site_id}
Sections: {", ".join(section_stack[:8])}
Brand Summary: {brand_summary[:300]}
Previous QA Critique:
{qa_critique[:800]}

Return a JSON object with:
{{
  "overallApproach": <string with high-level improvement strategy>,
  "sectionImprovements": [
    {{
      "sectionTitle": <string>,
      "currentIssues": [<string>, ...],
      "recommendedChanges": [<string>, ...],
      "priority": <"high" | "medium" | "low">
    }}
  ],
  "estimatedNewScore": <integer 75-95>,
  "implementationNotes": <string with key points>
}}

Only return valid JSON."""

            improvement_response = await client.generate_text(
                prompt=improvement_prompt,
                temperature=0.6,
                max_tokens=1500,
            )

            try:
                improvement_result = client.extract_json_from_response(
                    improvement_response
                )
            except ValueError as e:
                logger.error(f"Failed to parse improvement response for {site_id}: {e}")
                improvement_result = {
                    "overallApproach": "Manual review recommended",
                    "sectionImprovements": [],
                    "estimatedNewScore": 75,
                    "implementationNotes": improvement_response[:300],
                }

            return improvement_result
        except Exception as e:
            logger.error(f"Improvement brief generation failed for {site_id}: {e}")
            raise

    def compare_screenshots(
        self,
        screenshot1: bytes,
        screenshot2: bytes,
    ) -> float:
        """
        Compare two screenshots by computing hash similarity.
        Returns a similarity score (0-1) where 1.0 is identical.

        Args:
            screenshot1: First PNG screenshot bytes
            screenshot2: Second PNG screenshot bytes

        Returns:
            Similarity score (0-1)
        """
        hash1 = hashlib.sha256(screenshot1).hexdigest()
        hash2 = hashlib.sha256(screenshot2).hexdigest()
        return 1.0 if hash1 == hash2 else 0.0


# Singleton instance
_analyzer: Optional[ScreenshotAnalyzer] = None


def get_screenshot_analyzer() -> ScreenshotAnalyzer:
    """Get or create screenshot analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ScreenshotAnalyzer()
    return _analyzer
