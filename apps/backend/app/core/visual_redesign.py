from __future__ import annotations

import json
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
            "description": "Split layout with editorial feel, image on right",
        },
        {
            "id": "hero-centered",
            "name": "Centered Hero",
            "description": "Centered hero with headline, subheading, and primary CTA",
        },
        {
            "id": "services-bento",
            "name": "Bento Services",
            "description": "2x3 grid bento layout for services/features",
        },
        {
            "id": "services-grid",
            "name": "Simple Services Grid",
            "description": "Clean 3-column grid",
        },
        {
            "id": "proof-carousel",
            "name": "Testimonial Carousel",
            "description": "Scrollable testimonials with motion",
        },
        {
            "id": "proof-grid",
            "name": "Proof Grid",
            "description": "2x2 grid of proof points",
        },
        {
            "id": "gallery-masonry",
            "name": "Masonry Gallery",
            "description": "Premium image grid with masonry layout",
        },
        {
            "id": "timeline-vertical",
            "name": "Vertical Timeline",
            "description": "Step-by-step process with timeline",
        },
        {
            "id": "editorial-feature",
            "name": "Editorial Feature",
            "description": "Large featured section with image, headline, body, and bullet points",
        },
        {
            "id": "cta-banner",
            "name": "CTA Banner",
            "description": "High-impact CTA section with headline and action",
        },
        {
            "id": "cta-sticky",
            "name": "Sticky CTA",
            "description": "Sticky footer CTA that appears during scroll",
        },
    ]

    def __init__(self):
        self.gemini = get_llm_client()

    def _build_section_analysis_prompt(
        self,
        section: ExtractedSection,
        client_brand: dict[str, Any],
        section_index: int,
    ) -> str:
        """Build prompt for analyzing a single section."""
        
        components_list = "\n".join(
            f"- {c['id']}: {c['description']}"
            for c in self.AVAILABLE_COMPONENTS
        )

        prompt = f"""You are a premium web designer analyzing a website section for redesign.

SECTION #{section_index}
- Type: {section.type}
- Heading: {section.heading or 'N/A'}
- Body: {section.text[:200] if section.text else 'N/A'}
- CTAs: {', '.join(section.ctas[:3]) if section.ctas else 'N/A'}

CLIENT BRAND:
- Palette Mode: {client_brand.get('paletteMode', 'light')}
- Primary Color: {client_brand.get('primaryColor', {}).get('value', '#000')}
- Secondary Color: {client_brand.get('secondaryColor', {}).get('value', '#666')}
- Accent Color: {client_brand.get('accentColor', {}).get('value', '#f97316')}
- Typography: {client_brand.get('typography', {}).get('value', 'sans-serif')}
- Motion: {client_brand.get('motionIntensity', {}).get('value', 'subtle')}

AVAILABLE COMPONENTS:
{components_list}

TASK: Analyze this section and recommend the best premium component for redesign.

Consider:
1. Section type and content
2. Client brand identity
3. Visual hierarchy and layout
4. Premium design principles
5. Uniqueness and bespoke feel

Return ONLY valid JSON (no markdown, no explanation):
{{
  "sectionType": "{section.type}",
  "originalStrengths": ["strength1", "strength2"],
  "originalWeaknesses": ["weakness1", "weakness2"],
  "redesignGoal": "What to improve",
  "contentToReuse": ["content1", "content2"],
  "contentToRewrite": ["content1"],
  "recommendedComponent": "component-id",
  "visualDirection": "Description of visual treatment",
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
            
            # Validate componentId
            valid_ids = {c["id"] for c in self.AVAILABLE_COMPONENTS}
            if data.get("recommendedComponent") not in valid_ids:
                logger.warning(
                    f"Invalid componentId: {data.get('recommendedComponent')}, "
                    f"falling back to default"
                )
                data["recommendedComponent"] = "services-grid"
            
            return VisualCritique(**data)
        
        except Exception as e:
            logger.error(f"Failed to analyze section {section_index}: {e}")
            # Return safe default
            return VisualCritique(
                sectionType=section.type,
                redesignGoal="Improve visual presentation",
                contentToReuse=section.ctas[:2] if section.ctas else [],
                recommendedComponent="services-grid",
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
            critique = await self.analyze_section(
                section, client_brand, idx
            )
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
