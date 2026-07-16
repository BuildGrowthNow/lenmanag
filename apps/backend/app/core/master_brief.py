"""
Master Brief Generation - AI-powered strategic brief creation.

This module replaces the deterministic brief building with AI-generated
master briefs that serve as the creative and strategic foundation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.llm import get_llm_client
from app.schemas.brief import BrandAssets, MasterBrief, MasterBriefSection
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def generate_master_brief(
    *,
    lead_id: str,
    extraction: ExtractionSnapshot,
    feedback: str | None = None,
    previous_brief: MasterBrief | None = None,
) -> MasterBrief:
    """
    Generate a master brief using AI from extraction data.

    Args:
        lead_id: Lead identifier
        extraction: Extraction snapshot with all source data
        feedback: Optional user feedback for refinement
        previous_brief: Previous brief version if regenerating

    Returns:
        AI-generated MasterBrief
    """
    llm = get_llm_client()

    # Build extraction summary
    extraction_summary = _build_extraction_summary(extraction)

    # Build prompt
    if feedback and previous_brief:
        prompt = _build_refinement_prompt(
            extraction_summary=extraction_summary,
            previous_brief=previous_brief,
            feedback=feedback,
        )
    else:
        prompt = _build_initial_prompt(extraction_summary=extraction_summary)

    # Call LLM
    response = await llm.generate_text(
        prompt=prompt,
        temperature=0.7,
        max_tokens=4096,
    )

    # Parse structured response
    brief_data = llm.extract_json_from_response(response)

    # Build master brief
    master_brief = _build_master_brief_from_response(
        lead_id=lead_id,
        extraction=extraction,
        brief_data=brief_data,
        feedback=feedback,
        previous_brief=previous_brief,
    )

    return master_brief


def _build_extraction_summary(extraction: ExtractionSnapshot) -> str:
    """Build a concise summary of extraction data for the LLM prompt."""
    summary_parts = []

    # Company info
    summary_parts.append("## Company Information")
    summary_parts.append(f"Name: {extraction.summary.companyName or 'Unknown'}")

    # Use analyzed positioning (not raw meta tags)
    if extraction.analysis and extraction.analysis.positioning:
        summary_parts.append(f"Positioning: {extraction.analysis.positioning}")
    elif extraction.summary.positioningSummary:
        summary_parts.append(f"Positioning: {extraction.summary.positioningSummary}")

    # Use analyzed services (real descriptions, not headings)
    if extraction.analysis and extraction.analysis.services:
        summary_parts.append("\n## Services & Offerings")
        for service in extraction.analysis.services[:8]:
            summary_parts.append(f"- {service}")
    elif extraction.summary.serviceClues:
        summary_parts.append("\n## Services")
        for service in extraction.summary.serviceClues[:10]:
            summary_parts.append(f"- {service}")

    # Use analyzed audience (synthesized description)
    if extraction.analysis and extraction.analysis.audience:
        summary_parts.append("\n## Target Audience")
        summary_parts.append(extraction.analysis.audience)
    elif extraction.summary.audienceClues:
        summary_parts.append("\n## Target Audience")
        for audience in extraction.summary.audienceClues[:5]:
            summary_parts.append(f"- {audience}")

    # Use analyzed tone (synthesized description)
    if extraction.analysis and extraction.analysis.tone:
        summary_parts.append("\n## Tone & Voice")
        summary_parts.append(extraction.analysis.tone)
    elif extraction.summary.toneClues:
        summary_parts.append("\n## Tone & Voice")
        for tone in extraction.summary.toneClues[:3]:
            summary_parts.append(f"- {tone}")

    # Use analyzed primary CTAs
    if extraction.analysis and extraction.analysis.primaryCTAs:
        summary_parts.append("\n## Primary CTAs")
        for cta in extraction.analysis.primaryCTAs:
            summary_parts.append(f"- {cta}")
    elif extraction.summary.ctaClues:
        summary_parts.append("\n## CTA Buttons Found")
        for cta in extraction.summary.ctaClues[:5]:
            summary_parts.append(f"- {cta}")

    # Use analyzed value proposition
    if extraction.analysis and extraction.analysis.valueProposition:
        summary_parts.append("\n## Value Proposition")
        summary_parts.append(extraction.analysis.valueProposition)

    # Brand assets (unchanged - these are fine)
    if extraction.brandAssetCues:
        summary_parts.append("\n## Brand Assets")
        colors = [c for c in extraction.brandAssetCues if c.assetType == "color"]
        if colors:
            summary_parts.append(f"Colors: {', '.join(c.value for c in colors[:3])}")

        logos = [c for c in extraction.brandAssetCues if c.assetType == "logo"]
        if logos:
            summary_parts.append(f"Logo: {logos[0].label}")

        fonts = [c for c in extraction.brandAssetCues if c.assetType == "typography"]
        if fonts:
            summary_parts.append(f"Typography: {fonts[0].value}")

    # Analysis confidence indicator
    if extraction.analysis and extraction.analysis.confidence > 0:
        summary_parts.append(
            f"\n## Analysis Confidence: {extraction.analysis.confidence}%"
        )

    return "\n".join(summary_parts)


def _build_initial_prompt(extraction_summary: str) -> str:
    """Build the initial master brief generation prompt."""
    prompt = f"""You are a landing page strategist. Given the following ANALYZED data about a business, create a master brief for a high-converting landing page.

IMPORTANT: This data has been pre-analyzed by AI. The services, tone, and audience descriptions are already synthesized - use them as-is, don't try to re-interpret them.

{extraction_summary}

## Constraints
- This is a SINGLE landing page (not a multi-page site)
- Keep all content concise - headlines under 8 words, descriptions under 2 sentences
- The page must have a clear conversion goal
- Choose 4-7 sections maximum
- Be specific about visual direction - not generic
- DO NOT generate empty or placeholder fields - every field must have real content

## Output Format
Return a JSON object with this structure:
{{
  "businessGoal": "What this landing page should achieve (specific, not generic)",
  "primaryAudience": "Who we're talking to (use the analyzed audience data)",
  "conversionAction": "The one thing we want them to do (use the primary CTA)",
  "valueProposition": "Why they should care (use analyzed value prop, expand if needed)",
  "toneAndVoice": "How we sound (use the analyzed tone)",
  "visualStyle": "Description of look/feel (be specific, not 'clean and modern')",
  "colorStrategy": "How colors should be used (specific strategy)",
  "motionLevel": "none|subtle|moderate|dramatic",
  "specialEffects": ["3d-hero", "parallax-scroll"] or [],
  "headline": "Main hero headline (8 words max, compelling)",
  "subheadline": "Supporting line (2 sentences max)",
  "sections": [
    {{
      "purpose": "social-proof|services|process|cta|about|etc",
      "headline": "Section headline (clear, specific)",
      "contentSummary": "What goes in this section (detailed, not vague)",
      "suggestedApproach": "testimonial carousel, bento grid, icon list, etc",
      "contentPoints": ["key point 1 (specific)", "key point 2 (specific)", "key point 3"]
    }}
  ],
  "ctaStrategy": "Primary + secondary CTAs approach (be specific)",
  "aiReasoning": "Why these choices were made based on the analyzed data",
  "confidenceScore": 85
}}

CRITICAL: Every field must be populated with real, specific content. No empty arrays, no generic descriptions, no "TBD" placeholders.

Return ONLY valid JSON, no markdown formatting."""

    return prompt


def _build_refinement_prompt(
    extraction_summary: str,
    previous_brief: MasterBrief,
    feedback: str,
) -> str:
    """Build a refinement prompt incorporating user feedback."""
    previous_summary = {
        "businessGoal": previous_brief.businessGoal,
        "headline": previous_brief.headline,
        "sections": [
            {"purpose": s.purpose, "headline": s.headline}
            for s in previous_brief.sections
        ],
        "visualStyle": previous_brief.visualStyle,
        "motionLevel": previous_brief.motionLevel,
    }

    prompt = f"""You are a landing page strategist. Refine the master brief based on user feedback.

## Original Extraction Data
{extraction_summary}

## Previous Brief Summary
{json.dumps(previous_summary, indent=2)}

## User Feedback
{feedback}

## Task
Regenerate the master brief incorporating the user's feedback. Keep what works, change what they requested.

## Output Format
Return a JSON object with this structure:
{{
  "businessGoal": "What this landing page should achieve",
  "primaryAudience": "Who we're talking to",
  "conversionAction": "The one thing we want them to do",
  "valueProposition": "Why they should care (1-2 sentences)",
  "toneAndVoice": "How we sound (casual/professional/bold/etc)",
  "visualStyle": "Description of look/feel",
  "colorStrategy": "How colors should be used",
  "motionLevel": "none|subtle|moderate|dramatic",
  "specialEffects": ["3d-hero", "parallax-scroll"],
  "headline": "Main hero headline",
  "subheadline": "Supporting line",
  "sections": [
    {{
      "purpose": "social-proof|services|process|cta|etc",
      "headline": "Section headline",
      "contentSummary": "What goes in this section",
      "suggestedApproach": "testimonial carousel, bento grid, etc",
      "contentPoints": ["key point 1", "key point 2"]
    }}
  ],
  "ctaStrategy": "Primary + secondary CTAs approach",
  "aiReasoning": "Why these choices were made and how feedback was incorporated",
  "confidenceScore": 85
}}

Return ONLY valid JSON, no markdown formatting."""

    return prompt


def _build_master_brief_from_response(
    *,
    lead_id: str,
    extraction: ExtractionSnapshot,
    brief_data: dict[str, Any],
    feedback: str | None,
    previous_brief: MasterBrief | None,
) -> MasterBrief:
    """Build MasterBrief object from LLM response."""
    # Extract brand assets
    brand_assets = BrandAssets()
    if extraction.brandAssetCues:
        colors = [c for c in extraction.brandAssetCues if c.assetType == "color"]
        if colors:
            brand_assets.primaryColor = colors[0].value
            if len(colors) > 1:
                brand_assets.secondaryColor = colors[1].value

        logos = [c for c in extraction.brandAssetCues if c.assetType == "logo"]
        if logos:
            brand_assets.logoUrl = logos[0].sourceUrl

        fonts = [c for c in extraction.brandAssetCues if c.assetType == "typography"]
        if fonts:
            brand_assets.fontFamily = fonts[0].value

        images = [c for c in extraction.brandAssetCues if c.assetType == "image"]
        brand_assets.imageUrls = [img.sourceUrl for img in images[:5]]

    # Extract content - prefer analyzed data, fall back to keywords
    extracted_content: dict[str, list[str]] = {}
    if extraction.analysis and extraction.analysis.services:
        extracted_content["services"] = extraction.analysis.services[:8]
    elif extraction.summary.serviceClues:
        extracted_content["services"] = extraction.summary.serviceClues[:10]

    if extraction.analysis and extraction.analysis.audience:
        extracted_content["audiences"] = [extraction.analysis.audience]
    elif extraction.summary.audienceClues:
        extracted_content["audiences"] = extraction.summary.audienceClues[:5]

    if extraction.analysis and extraction.analysis.tone:
        extracted_content["tones"] = [extraction.analysis.tone]
    elif extraction.summary.toneClues:
        extracted_content["tones"] = extraction.summary.toneClues[:3]

    if extraction.analysis and extraction.analysis.primaryCTAs:
        extracted_content["primaryCTAs"] = extraction.analysis.primaryCTAs[:3]
    elif extraction.summary.ctaClues:
        extracted_content["primaryCTAs"] = extraction.summary.ctaClues[:5]

    if extraction.analysis and extraction.analysis.valueProposition:
        extracted_content["valueProposition"] = [extraction.analysis.valueProposition]
    if extraction.analysis and extraction.analysis.positioning:
        extracted_content["positioning"] = [extraction.analysis.positioning]

    # Build sections
    sections = []
    for section_data in brief_data.get("sections", [])[:7]:
        sections.append(
            MasterBriefSection(
                purpose=section_data.get("purpose", "section"),
                headline=section_data.get("headline", "Section"),
                contentSummary=section_data.get("contentSummary", ""),
                suggestedApproach=section_data.get("suggestedApproach", ""),
                contentPoints=section_data.get("contentPoints", []),
            )
        )

    # Determine version
    version = 1
    if previous_brief:
        version = previous_brief.version + 1

    # Build feedback history
    feedback_history = []
    if previous_brief:
        feedback_history = list(previous_brief.feedbackHistory)
    if feedback:
        feedback_history.append(feedback)

    # Validate motion level
    motion_level = brief_data.get("motionLevel", "subtle")
    if motion_level not in ["none", "subtle", "moderate", "dramatic"]:
        motion_level = "subtle"

    master_brief = MasterBrief(
        id=str(uuid4()),
        leadId=lead_id,
        sourceExtractionId=extraction.id,
        sourceExtractionVersion=extraction.version,
        version=version,
        approvalState="needs_review",
        businessGoal=brief_data.get("businessGoal", "Generate qualified leads"),
        primaryAudience=brief_data.get("primaryAudience", "Unknown audience"),
        conversionAction=brief_data.get("conversionAction", "Contact us"),
        valueProposition=brief_data.get("valueProposition", ""),
        toneAndVoice=brief_data.get("toneAndVoice", "Professional"),
        visualStyle=brief_data.get("visualStyle", "Clean and modern"),
        colorStrategy=brief_data.get("colorStrategy", "Neutral with subtle accents"),
        motionLevel=motion_level,
        specialEffects=brief_data.get("specialEffects", []),
        headline=brief_data.get(
            "headline", extraction.summary.companyName or "Welcome"
        ),
        subheadline=brief_data.get("subheadline", ""),
        sections=sections,
        ctaStrategy=brief_data.get(
            "ctaStrategy", "Primary CTA: Contact, Secondary: Learn More"
        ),
        extractedContent=extracted_content,
        brandAssets=brand_assets,
        competitorInsights="",
        confidenceScore=min(100, max(0, brief_data.get("confidenceScore", 75))),
        aiReasoning=brief_data.get("aiReasoning", "Generated from extraction data"),
        missingRequirements=[],
        feedbackHistory=feedback_history,
        createdAt=_now(),
        updatedAt=_now(),
    )

    return master_brief
