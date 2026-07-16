"""
Extraction Enrichment — Phase 1 Content Quality

After the heuristic crawler finishes, this module:
1. Validates extraction content quality (min thresholds)
2. Uses LLM to infer services/audience/positioning from extracted text
3. Returns enriched summary data to be merged into the crawl result
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.llm import get_llm_client

logger = logging.getLogger(__name__)

MIN_CONTENT_CHARS = 500
MIN_SERVICES = 3
MIN_AUDIENCE_CLUES = 2


def validate_extraction_content(crawl_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that extraction captured enough usable content for site generation.
    Returns (is_valid, list_of_issues).
    """
    issues: list[str] = []
    summary = crawl_data.get("summary", {})
    sections = crawl_data.get("sectionInventory", [])

    total_text = sum(len(s.get("text") or "") for s in sections)
    page_text = sum(
        len(p.get("cleanedText") or "") for p in crawl_data.get("pageInventory", [])
    )
    total_content = total_text + page_text

    if total_content < MIN_CONTENT_CHARS:
        issues.append(
            f"Only {total_content} chars extracted, need {MIN_CONTENT_CHARS}+ for enrichment"
        )

    if len(summary.get("serviceClues", [])) < MIN_SERVICES:
        issues.append(
            f"Only {len(summary.get('serviceClues', []))} services found, need {MIN_SERVICES}+"
        )

    if len(summary.get("audienceClues", [])) < MIN_AUDIENCE_CLUES:
        issues.append(
            f"Only {len(summary.get('audienceClues', []))} audience clues, need {MIN_AUDIENCE_CLUES}+"
        )

    if (
        not summary.get("positioningSummary")
        or len(summary.get("positioningSummary", "")) < 30
    ):
        issues.append("Positioning summary too short or missing")

    return (len(issues) == 0, issues)


def _gather_content_for_llm(crawl_data: dict[str, Any]) -> str:
    """Collect all extracted text into a single context block for LLM analysis."""
    parts: list[str] = []

    for page in crawl_data.get("pageInventory", []):
        if page.get("title"):
            parts.append(f"Page: {page['title']}")
        if page.get("cleanedText"):
            parts.append(page["cleanedText"][:2000])
        if page.get("summary"):
            parts.append(page["summary"])

    for section in crawl_data.get("sectionInventory", []):
        heading = section.get("heading") or ""
        text = section.get("text") or ""
        if heading or text:
            parts.append(f"{heading}: {text[:500]}" if heading else text[:500])

    combined = "\n".join(parts)
    return combined[:12000]


async def enrich_extraction(crawl_data: dict[str, Any]) -> dict[str, Any]:
    """
    When heuristic extraction is sparse, use LLM to infer services, audience,
    and positioning from whatever text WAS extracted.

    Mutates crawl_data['summary'] in-place and returns it for convenience.
    Only enriches fields that are below minimum thresholds.
    """
    summary = crawl_data.get("summary", {})
    content = _gather_content_for_llm(crawl_data)

    if len(content.strip()) < MIN_CONTENT_CHARS:
        logger.warning(
            "Not enough content for LLM enrichment (%d chars). Skipping.",
            len(content.strip()),
        )
        if "content_too_sparse_for_enrichment" not in crawl_data.get("gapItems", []):
            crawl_data.setdefault("gapItems", []).append(
                "content_too_sparse_for_enrichment"
            )
        return summary

    llm = get_llm_client()
    company_name = summary.get("companyName") or "this company"
    enriched_any = False

    if len(summary.get("serviceClues", [])) < MIN_SERVICES:
        services = await _infer_services(llm, company_name, content)
        if services:
            existing = set(summary.get("serviceClues", []))
            merged = list(existing | set(services))[:8]
            summary["serviceClues"] = merged
            enriched_any = True
            logger.info("Enriched serviceClues: %s", merged)

    if len(summary.get("audienceClues", [])) < MIN_AUDIENCE_CLUES:
        audience = await _infer_audience(llm, company_name, content)
        if audience:
            existing = set(summary.get("audienceClues", []))
            existing.discard(
                "Audience not explicit in public metadata; review manually."
            )
            merged = list(existing | set(audience))[:6]
            summary["audienceClues"] = merged
            enriched_any = True
            logger.info("Enriched audienceClues: %s", merged)

    if (
        not summary.get("positioningSummary")
        or len(summary.get("positioningSummary", "")) < 30
    ):
        positioning = await _infer_positioning(llm, company_name, content)
        if positioning:
            summary["positioningSummary"] = positioning
            enriched_any = True
            logger.info("Enriched positioningSummary: %s", positioning[:80])

    if enriched_any:
        if "llm_enriched" not in crawl_data.get("gapItems", []):
            crawl_data.setdefault("gapItems", []).append("llm_enriched")
        logger.info("LLM enrichment completed for %s", company_name)
    else:
        logger.info("LLM enrichment produced no new data for %s", company_name)

    crawl_data["summary"] = summary
    return summary


async def _infer_services(llm: Any, company_name: str, content: str) -> list[str]:
    """Use LLM to identify services/offerings from extracted text."""
    prompt = f"""You are analyzing extracted website content for "{company_name}".

Based ONLY on the text below, identify 3-8 specific services, products, or offerings this company provides.

Rules:
- Only list services/products clearly mentioned or described in the text
- Use short, clear labels (2-5 words each)
- Do NOT invent services not supported by the text
- Do NOT include generic terms like "solutions" or "services" without specifics
- If you cannot identify at least 3 from the text, return what you can find

EXTRACTED CONTENT:
{content[:6000]}

Return ONLY a JSON array of strings. Example: ["Payment processing", "Fraud detection", "Billing management"]
No other text, no explanation."""

    try:
        response = await llm.generate_text(prompt, temperature=0.3, max_tokens=300)
        data = llm.extract_json_from_response(response)
        if isinstance(data, list):
            return [str(s).strip() for s in data if s and len(str(s).strip()) > 2][:8]
        if isinstance(data, dict) and "services" in data:
            return [str(s).strip() for s in data["services"] if s][:8]
        return []
    except Exception as e:
        logger.warning("Service inference failed: %s", e)
        return []


async def _infer_audience(llm: Any, company_name: str, content: str) -> list[str]:
    """Use LLM to identify target audience from extracted text."""
    prompt = f"""You are analyzing extracted website content for "{company_name}".

Based ONLY on the text below, identify 2-5 target audience segments this company serves.

Rules:
- Only identify audiences mentioned or clearly implied in the text
- Use the format "For [audience]" (e.g., "For small businesses", "For developers")
- Do NOT invent audiences not supported by the text
- Be specific where possible (not just "For everyone")

EXTRACTED CONTENT:
{content[:4000]}

Return ONLY a JSON array of strings. Example: ["For startups", "For enterprise teams", "For developers"]
No other text, no explanation."""

    try:
        response = await llm.generate_text(prompt, temperature=0.3, max_tokens=200)
        data = llm.extract_json_from_response(response)
        if isinstance(data, list):
            return [str(s).strip() for s in data if s and len(str(s).strip()) > 3][:6]
        return []
    except Exception as e:
        logger.warning("Audience inference failed: %s", e)
        return []


async def _infer_positioning(llm: Any, company_name: str, content: str) -> str | None:
    """Use LLM to generate positioning summary from extracted text."""
    prompt = f"""You are analyzing extracted website content for "{company_name}".

Based ONLY on the text below, write a 2-3 sentence positioning summary that captures:
- What the company does (specific services/products)
- Who it serves (target audience/market)
- What makes it different or valuable (unique value proposition if apparent)

Rules:
- Only state facts supported by the text
- Aim for 150-300 characters of meaningful content
- Write in third person ("Company X provides...")
- Be specific about services and value, not generic ("provides solutions")
- Do NOT invent claims not in the text

EXTRACTED CONTENT:
{content[:6000]}

Return ONLY the positioning summary text, no quotes, no JSON, no explanation."""

    try:
        response = await llm.generate_text(prompt, temperature=0.3, max_tokens=300)
        result = response.strip().strip('"').strip("'")
        # Ensure meaningful length - if too short, it's likely just a title
        if len(result) > 40:
            return result[:400]
        logger.warning(
            "Positioning inference too short (%d chars): %s", len(result), result
        )
        return None
    except Exception as e:
        logger.warning("Positioning inference failed: %s", e)
        return None
