from __future__ import annotations

import logging
from typing import Any

from app.core.llm import get_llm_client
from app.schemas.brief import VisualCritique, VisualRedesignBrief, SiteBrief
from app.schemas.extraction import ExtractionSnapshot, ExtractedSection

logger = logging.getLogger(__name__)


class VisualRedesignAnalyzer:
    """Analyzes sections and generates visual redesign briefs using Gemini."""

    AVAILABLE_COMPONENTS = [
        {
            "id": "hero-split-editorial",
            "name": "Split Editorial Hero",
            "description": "Split layout with editorial feel, image on right, scroll-triggered animations",
            "interactivity": "scroll-reveal, hover-lift",
        },
        {
            "id": "hero-centered",
            "name": "Centered Hero",
            "description": "Centered hero with headline, subheading, and primary CTA with gradient background",
            "interactivity": "animated-gradient, pulse-cta",
        },
        {
            "id": "services-bento",
            "name": "Interactive Bento Grid",
            "description": "2x3 bento grid with hover effects, expandable cards, and micro-interactions",
            "interactivity": "hover-expand, stagger-reveal, card-tilt",
        },
        {
            "id": "services-tabs",
            "name": "Tabbed Services",
            "description": "Interactive tab navigation for services with smooth transitions",
            "interactivity": "tab-switching, slide-transitions",
        },
        {
            "id": "services-accordion",
            "name": "Service Accordion",
            "description": "Collapsible accordion sections for detailed service info",
            "interactivity": "expand-collapse, smooth-accordion",
        },
        {
            "id": "proof-carousel",
            "name": "Auto-rotating Carousel",
            "description": "Auto-rotating testimonials with drag controls and pagination",
            "interactivity": "auto-rotate, drag-scroll, dot-navigation",
        },
        {
            "id": "proof-grid-interactive",
            "name": "Interactive Proof Grid",
            "description": "Grid with hover overlays, quote expansions, and filter buttons",
            "interactivity": "hover-overlay, modal-expand, filter-animation",
        },
        {
            "id": "gallery-masonry",
            "name": "Lightbox Gallery",
            "description": "Masonry grid with hover zoom and lightbox modal on click",
            "interactivity": "hover-zoom, lightbox-modal, lazy-load",
        },
        {
            "id": "timeline-vertical",
            "name": "Animated Timeline",
            "description": "Vertical timeline with scroll-triggered progress line animation",
            "interactivity": "scroll-progress, fade-in-sequence",
        },
        {
            "id": "stats-counter",
            "name": "Animated Stats Counter",
            "description": "Number counters that animate from 0 when scrolled into view",
            "interactivity": "count-up-animation, scroll-trigger",
        },
        {
            "id": "features-comparison",
            "name": "Feature Comparison Table",
            "description": "Interactive comparison table with toggle switches and highlights",
            "interactivity": "toggle-columns, row-highlight, sticky-header",
        },
        {
            "id": "video-hero",
            "name": "Video Background Hero",
            "description": "Hero section with background video and overlay content",
            "interactivity": "video-background, parallax-scroll",
        },
        {
            "id": "cta-banner",
            "name": "Animated CTA Banner",
            "description": "High-impact CTA with animated gradient and pulse effect",
            "interactivity": "gradient-animation, button-pulse",
        },
        {
            "id": "cta-sticky",
            "name": "Sticky Slide-in CTA",
            "description": "CTA that slides in from bottom after scroll threshold",
            "interactivity": "scroll-trigger-slide, dismiss-animation",
        },
    ]

    def __init__(self):
        self.gemini = get_llm_client()

    def _validate_and_fix_component_id(
        self, component_id: str | None, section_type: str
    ) -> str:
        """
        Validate component ID and fix common errors.
        Returns a valid component ID, converting PascalCase if needed.
        """
        if not component_id:
            return self._fallback_component_for_section(section_type)

        valid_ids = {c["id"] for c in self.AVAILABLE_COMPONENTS}

        # Already valid
        if component_id in valid_ids:
            return component_id

        # Try converting PascalCase to kebab-case
        # "HeroSplitEditorial" -> "hero-split-editorial"
        import re

        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", component_id).lower()
        if kebab in valid_ids:
            logger.warning(f"Fixed component ID: {component_id} -> {kebab}")
            return kebab

        # Try common misspellings/variations
        normalized = component_id.lower().replace("_", "-")
        if normalized in valid_ids:
            logger.warning(f"Fixed component ID: {component_id} -> {normalized}")
            return normalized

        # Invalid - use fallback
        logger.error(
            f"Invalid component ID: {component_id}, using fallback for section type {section_type}"
        )
        return self._fallback_component_for_section(section_type)

    def _fallback_component_for_section(self, section_type: str) -> str:
        """Return safe default component for section type."""
        fallbacks = {
            "hero": "hero-split-editorial",
            "services": "services-bento",
            "proof": "proof-carousel",
            "about": "hero-split-editorial",
            "process": "timeline-vertical",
            "pricing": "features-comparison",
            "gallery": "gallery-masonry",
            "contact": "cta-banner",
            "cta": "cta-banner",
        }
        return fallbacks.get(section_type, "services-bento")

    def _build_section_analysis_prompt(
        self,
        section: ExtractedSection,
        client_brand: dict[str, Any],
        section_index: int,
    ) -> str:
        """Build prompt for analyzing a single section."""

        components_list = "\n".join(
            f"- {c['id']}: {c['description']}" for c in self.AVAILABLE_COMPONENTS
        )

        prompt = f"""You are a premium, interactive web designer analyzing a website section for redesign.

SECTION #{section_index}
- Type: {section.type}
- Heading: {section.heading or "N/A"}
- Body: {section.text[:200] if section.text else "N/A"}
- CTAs: {", ".join(section.ctas[:3]) if section.ctas else "N/A"}

CLIENT BRAND:
- Palette Mode: {client_brand.get("paletteMode", "light")}
- Primary Color: {client_brand.get("primaryColor", {}).get("value", "#000")}
- Secondary Color: {client_brand.get("secondaryColor", {}).get("value", "#666")}
- Accent Color: {client_brand.get("accentColor", {}).get("value", "#f97316")}
- Typography: {client_brand.get("typography", {}).get("value", "sans-serif")}
- Motion: {client_brand.get("motionIntensity", {}).get("value", "subtle")}

AVAILABLE COMPONENTS (use exact kebab-case IDs):
{components_list}

IMPORTANT: Return component IDs in kebab-case format (e.g., "hero-split-editorial" NOT "HeroSplitEditorial")

DESIGN REQUIREMENTS:
- AVOID generic card layouts without interactivity
- PRIORITIZE components with hover effects, animations, and user interactions
- For service sections: prefer tabs, accordions, or interactive bento grids over static cards
- For proof/testimonials: use carousels, filterable grids, or expandable quote cards
- For stats/metrics: use animated counters that trigger on scroll
- For features: use comparison tables, toggle switches, or expandable feature lists
- Add motion: scroll-triggered reveals, hover lifts, gradient animations, smooth transitions
- If content is rich enough, choose the MORE interactive variant

TASK: Analyze this section and recommend the MOST INTERACTIVE premium component that fits the content.

Consider:
1. Section type and content richness
2. Opportunity for interactivity (tabs, accordions, carousels, counters, toggles)
3. Engagement potential - how can users interact with this?
4. Scroll-triggered animations and micro-interactions
5. Avoiding static "card grid" patterns unless content is minimal
6. Premium design principles: motion, depth, responsiveness

Return ONLY valid JSON (no markdown, no explanation):
{{
  "sectionType": "{section.type}",
  "originalStrengths": ["strength1", "strength2"],
  "originalWeaknesses": ["weakness1", "weakness2"],
  "redesignGoal": "What to improve with interactivity",
  "contentToReuse": ["content1", "content2"],
  "contentToRewrite": ["content1"],
  "recommendedComponent": "component-id",
  "visualDirection": "Description of interactive visual treatment with specific animations/interactions",
  "confidence": 85
}}"""

        return prompt

    async def analyze_section(
        self,
        section: ExtractedSection,
        client_brand: dict[str, Any],
        section_index: int,
    ) -> VisualCritique:
        """Analyze a single section and generate redesign critique."""

        prompt = self._build_section_analysis_prompt(
            section, client_brand, section_index
        )

        try:
            response = await self.gemini.generate_text(
                prompt,
                temperature=0.7,
                max_tokens=1024,
            )

            data = self.gemini.extract_json_from_response(response)

            # Validate and fix componentId
            component_id = self._validate_and_fix_component_id(
                data.get("recommendedComponent"), section.type
            )
            data["recommendedComponent"] = component_id

            return VisualCritique(**data)

        except Exception as e:
            logger.error(f"Failed to analyze section {section_index}: {e}")
            # Return safe default
            return VisualCritique(
                sectionType=section.type,
                redesignGoal="Improve visual presentation",
                contentToReuse=section.ctas[:2] if section.ctas else [],
                recommendedComponent=self._fallback_component_for_section(section.type),
                visualDirection="Clean, professional layout",
                confidence=40,
            )

    async def generate_redesign_brief(
        self,
        brief: SiteBrief,
        extraction: ExtractionSnapshot,
        client_brand: dict[str, Any],
    ) -> list[VisualRedesignBrief]:
        """Generate visual redesign brief for all sections."""

        redesign_briefs: list[VisualRedesignBrief] = []

        # Get sections from extraction
        sections = extraction.sectionInventory or []

        if not sections:
            logger.warning("No sections found in extraction")
            return redesign_briefs

        logger.info("Analyzing %d sections for visual redesign", len(sections))
        for s in sections:
            logger.info(
                "  - %s: type=%s, text_length=%d",
                getattr(s, "heading", None) or getattr(s, "id", "section"),
                getattr(s, "type", None),
                len(getattr(s, "text", "") or ""),
            )

        # For now, create a single redesign brief for the main page
        # since ExtractedSection doesn't have pageUrl
        critiques: list[VisualCritique] = []

        for idx, section in enumerate(sections[:10]):  # Limit to 10 sections
            critique = await self.analyze_section(section, client_brand, idx)
            critiques.append(critique)

        if critiques:
            redesign_brief = VisualRedesignBrief(
                pageUrl=extraction.canonicalWebsiteUrl or "homepage",
                critiques=critiques,
                artDirection=brief.toneProfile.value or "minimal-luxe",
            )
            redesign_briefs.append(redesign_brief)

        logger.info(
            "Generated visual redesign brief with %d recommendations",
            len(critiques),
        )
        logger.info("Generated %d visual redesign briefs", len(redesign_briefs))
        return redesign_briefs


async def generate_visual_redesign_brief(
    brief: SiteBrief,
    extraction: ExtractionSnapshot,
    client_brand: dict[str, Any],
) -> list[VisualRedesignBrief]:
    """Public function to generate visual redesign brief."""
    analyzer = VisualRedesignAnalyzer()
    return await analyzer.generate_redesign_brief(brief, extraction, client_brand)
