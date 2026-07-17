"""
Extraction Analysis — LLM-Powered Semantic Understanding

Replaces keyword-based heuristics with actual semantic analysis.
Runs after raw extraction, before master brief generation.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.llm import get_llm_client
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)


async def analyze_extraction(extraction: ExtractionSnapshot) -> dict[str, Any]:
    """
    Analyze raw extraction data using LLM to extract semantic meaning.

    This replaces ALL keyword-based detection with actual understanding:
    - Services: Real descriptions (not bare headings)
    - Tone: Synthesized voice description (not keyword matches)
    - CTAs: Primary conversion actions (not all buttons)
    - Audience: Synthesized target market (not keyword phrases)
    - Positioning: What they do and who for (not raw meta tags)

    Args:
        extraction: Raw extraction snapshot with HTML/text signals

    Returns:
        Dictionary with analyzed data:
        {
            "services": ["Service 1", "Service 2", ...],
            "tone": "Professional with friendly undertones...",
            "primaryCTAs": ["Schedule Consultation", "Get Quote"],
            "audience": "Homeowners in suburbs, ages 35-55, middle-income",
            "valueProposition": "What makes them different",
            "positioning": "Synthesized 2-3 sentence summary"
        }
    """
    llm = get_llm_client()

    # Gather content for analysis
    context = _build_analysis_context(extraction)

    # Single LLM call with structured output
    prompt = _build_analysis_prompt(context)

    try:
        response = await llm.generate_text(
            prompt=prompt,
            temperature=0.3,  # Lower temp for more consistent analysis
            max_tokens=2048,
        )

        # Parse structured JSON response
        analysis = llm.extract_json_from_response(response)

        # Validate and clean
        cleaned_analysis = _validate_analysis(analysis)

        logger.info(
            "Analysis complete: %d services, tone='%s', %d CTAs",
            len(cleaned_analysis.get("services", [])),
            cleaned_analysis.get("tone", "")[:50],
            len(cleaned_analysis.get("primaryCTAs", [])),
        )

        return cleaned_analysis

    except Exception as e:
        logger.error("LLM analysis failed: %s", e)
        # Return empty analysis rather than failing
        return _empty_analysis()


def _build_analysis_context(extraction: ExtractionSnapshot) -> dict[str, Any]:
    """Extract relevant content from extraction for LLM analysis."""

    # Gather all text content (homepage + top pages)
    all_text_chunks = []

    if extraction.pageInventory:
        for page in extraction.pageInventory[:3]:  # Homepage + 2 key pages
            if hasattr(page, "cleanedText") and page.cleanedText:
                all_text_chunks.append(page.cleanedText[:3000])
            elif hasattr(page, "summary") and page.summary:
                all_text_chunks.append(page.summary)

    # Section content
    section_texts = []
    section_headings = []
    if extraction.sectionInventory:
        for section in extraction.sectionInventory[:10]:
            if hasattr(section, "model_dump"):
                section_data = section.model_dump()
            else:
                section_data = dict(section) if hasattr(section, "__iter__") else {}

            if section_data.get("heading"):
                section_headings.append(section_data["heading"])
            if section_data.get("text"):
                section_texts.append(section_data["text"][:500])

    # All CTAs (buttons, links with action text)
    all_ctas = extraction.summary.ctaClues if extraction.summary.ctaClues else []

    # Pre-extracted testimonials (raw, need validation)
    raw_testimonials = []
    if extraction.extractedTestimonials:
        for t in extraction.extractedTestimonials[:10]:
            if hasattr(t, "model_dump"):
                raw_testimonials.append(t.model_dump())
            else:
                raw_testimonials.append(dict(t) if hasattr(t, "__iter__") else {})

    # Pre-extracted client logos
    raw_client_logos = []
    if extraction.extractedClientLogos:
        for logo in extraction.extractedClientLogos[:15]:
            if hasattr(logo, "model_dump"):
                raw_client_logos.append(logo.model_dump())
            else:
                raw_client_logos.append(dict(logo) if hasattr(logo, "__iter__") else {})

    return {
        "company_name": extraction.summary.companyName or "this company",
        "website_url": extraction.canonicalWebsiteUrl,
        "homepage_text": all_text_chunks[0] if all_text_chunks else "",
        "additional_pages_text": "\n\n".join(all_text_chunks[1:3]),
        "section_headings": section_headings,
        "section_texts": section_texts,
        "all_ctas": all_ctas[:20],
        "raw_positioning": extraction.summary.positioningSummary or "",
        "raw_testimonials": raw_testimonials,
        "raw_client_logos": raw_client_logos,
    }


def _build_analysis_prompt(context: dict[str, Any]) -> str:
    """Build the LLM prompt for extraction analysis."""

    # Format raw testimonials for validation
    testimonials_section = ""
    if context.get("raw_testimonials"):
        testimonials_section = "\n# Pre-Extracted Testimonials (need validation)\n"
        for i, t in enumerate(context["raw_testimonials"][:8], 1):
            testimonials_section += f'{i}. Quote: "{t.get("quote", "")[:200]}"\n'
            if t.get("authorName"):
                testimonials_section += f"   Author: {t.get('authorName')}"
                if t.get("authorTitle"):
                    testimonials_section += f", {t.get('authorTitle')}"
                if t.get("authorCompany"):
                    testimonials_section += f" at {t.get('authorCompany')}"
                testimonials_section += "\n"

    # Format raw client logos
    client_logos_section = ""
    if context.get("raw_client_logos"):
        client_logos_section = "\n# Pre-Extracted Client Logos (need validation)\n"
        for logo in context["raw_client_logos"][:10]:
            name = logo.get("companyName") or logo.get("altText") or "Unknown"
            client_logos_section += f"- {name}\n"

    prompt = f"""You are analyzing a business website to extract semantic meaning for landing page generation.

# Company Information
Name: {context["company_name"]}
Website: {context["website_url"]}

# Homepage Content
{context["homepage_text"][:6000]}

# Additional Page Content
{context["additional_pages_text"][:3000]}

# Section Headings Found
{chr(10).join(f"- {h}" for h in context["section_headings"][:15])}

# All CTA Buttons/Links Found
{chr(10).join(f"- {cta}" for cta in context["all_ctas"][:20])}
{testimonials_section}{client_logos_section}
---

## Task
Analyze this content and extract semantic meaning. Return a JSON object with:

1. **services** (array of strings): 3-8 actual services/products they offer
   - Use real descriptions, not generic headings
   - Example: "24/7 Emergency HVAC Repair" NOT "Services"

2. **tone** (string): Synthesized tone/voice description in 1-2 sentences
   - Examples: "Professional with friendly undertones, emphasizing trust and reliability"
   - NOT just keywords like "professional" or "friendly"

3. **primaryCTAs** (array of 1-3 strings): The PRIMARY conversion actions
   - Only the main CTAs (not "Contact Us" if there's a stronger CTA)
   - Example: ["Schedule Free Consultation", "Get Instant Quote"]

4. **audience** (string): Target audience in 1 sentence
   - Be specific: demographics, needs, context
   - Example: "Homeowners in suburbs experiencing HVAC issues, ages 35-55, middle-income"

5. **valueProposition** (string): What makes them different/valuable in 1-2 sentences
   - Not generic ("we provide great service")
   - Specific differentiators

6. **positioning** (string): Synthesized summary in 2-3 sentences
   - What they do, who they serve, how they're different
   - NOT just repeating meta tags

7. **confidence** (number 0-100): How confident you are in this analysis

8. **testimonials** (array of objects): Validated testimonials from the pre-extracted list
   - ONLY include testimonials that appear to be REAL customer quotes (not generic filler)
   - Clean up and rephrase for clarity if needed, but preserve the meaning
   - Each object: {{"quote": "...", "authorName": "...", "authorCompany": "...", "isVerified": true/false}}
   - NEVER invent testimonials - only validate/clean what was extracted

9. **clientLogos** (array of strings): Validated client/partner company names
   - ONLY include names that appear to be real companies (not generic icons)

## Rules
- Base answers ONLY on the content provided
- NEVER invent or fabricate testimonials, quotes, or company names
- If something is unclear, be conservative (lower confidence)
- Use the language of the content (if Spanish site, answer in Spanish)
- Be specific, not generic

Return ONLY valid JSON, no markdown formatting:
{{
  "services": ["Service 1", "Service 2"],
  "tone": "Tone description",
  "primaryCTAs": ["CTA 1", "CTA 2"],
  "audience": "Audience description",
  "valueProposition": "Value prop",
  "positioning": "Positioning summary",
  "confidence": 85,
  "testimonials": [{{"quote": "...", "authorName": "...", "authorCompany": "...", "isVerified": true}}],
  "clientLogos": ["Company A", "Company B"]
}}
"""

    return prompt


def _validate_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Validate and clean LLM analysis response."""

    # Validate testimonials
    validated_testimonials = []
    for t in analysis.get("testimonials", [])[:10]:
        if not isinstance(t, dict):
            continue
        quote = str(t.get("quote", "")).strip()
        if len(quote) < 20:  # Too short
            continue
        validated_testimonials.append(
            {
                "quote": quote[:500],
                "authorName": str(t.get("authorName", "")).strip()[:100] or None,
                "authorTitle": str(t.get("authorTitle", "")).strip()[:100] or None,
                "authorCompany": str(t.get("authorCompany", "")).strip()[:100] or None,
                "isVerified": bool(t.get("isVerified", False)),
            }
        )

    # Validate client logos
    validated_client_logos = []
    for logo in analysis.get("clientLogos", [])[:20]:
        name = str(logo).strip() if logo else ""
        if len(name) > 2 and name.lower() not in ["logo", "icon", "image", "unknown"]:
            validated_client_logos.append(
                {
                    "companyName": name[:100],
                }
            )

    return {
        "services": [
            str(s).strip()
            for s in analysis.get("services", [])
            if s and len(str(s).strip()) > 5
        ][:8],
        "tone": str(analysis.get("tone", "")).strip()[:500] or "Professional",
        "primaryCTAs": [
            str(c).strip()
            for c in analysis.get("primaryCTAs", [])
            if c and len(str(c).strip()) > 3
        ][:3],
        "audience": str(analysis.get("audience", "")).strip()[:300]
        or "General audience",
        "valueProposition": str(analysis.get("valueProposition", "")).strip()[:500]
        or "",
        "positioning": str(analysis.get("positioning", "")).strip()[:1000] or "",
        "confidence": min(100, max(0, int(analysis.get("confidence", 50)))),
        "testimonials": validated_testimonials,
        "clientLogos": validated_client_logos,
    }


def _empty_analysis() -> dict[str, Any]:
    """Return empty analysis when LLM fails."""
    return {
        "services": [],
        "tone": "Professional",
        "primaryCTAs": [],
        "audience": "General audience",
        "valueProposition": "",
        "positioning": "",
        "confidence": 0,
        "testimonials": [],
        "clientLogos": [],
    }
