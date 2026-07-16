"""
Content Rewriter

LLM-powered content rewriting for more impactful, concise, and engaging copy.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.design_prompts import build_content_rewrite_prompt
from app.core.llm import get_llm_client

logger = logging.getLogger(__name__)


async def rewrite_headline(
    original: str,
    industry: str,
    company_name: str,
    brand_tone: str,
) -> dict[str, Any]:
    """Rewrite headline for maximum impact."""

    prompt = build_content_rewrite_prompt(
        industry=industry,
        content_type="headline",
        original_content=original,
        company_name=company_name,
        brand_tone=brand_tone,
    )

    llm = get_llm_client()
    try:
        response = await llm.generate_text(prompt=prompt, max_tokens=150)
        rewritten = response.strip().strip('"').strip("'")

        return {
            "original": original,
            "rewritten": rewritten,
            "type": "headline",
            "confidence": 85,  # High confidence for LLM rewrites
        }
    except Exception as e:
        logger.warning(f"Headline rewrite failed: {e}, using original")
        return {
            "original": original,
            "rewritten": original,
            "type": "headline",
            "confidence": 50,
            "error": str(e),
        }


async def rewrite_subheadline(
    original: str,
    industry: str,
    company_name: str,
    brand_tone: str,
) -> dict[str, Any]:
    """Rewrite subheadline for clarity and impact."""

    prompt = build_content_rewrite_prompt(
        industry=industry,
        content_type="subheadline",
        original_content=original,
        company_name=company_name,
        brand_tone=brand_tone,
    )

    llm = get_llm_client()
    try:
        response = await llm.generate_text(prompt=prompt, max_tokens=200)
        rewritten = response.strip().strip('"').strip("'")

        return {
            "original": original,
            "rewritten": rewritten,
            "type": "subheadline",
            "confidence": 85,
        }
    except Exception as e:
        logger.warning(f"Subheadline rewrite failed: {e}, using original")
        return {
            "original": original,
            "rewritten": original,
            "type": "subheadline",
            "confidence": 50,
            "error": str(e),
        }


async def rewrite_services(
    services: list[str],
    industry: str,
    company_name: str,
    brand_tone: str,
) -> list[dict[str, Any]]:
    """Rewrite service names to be more descriptive and benefit-driven."""

    rewritten_services = []

    for service in services[:10]:  # Limit to first 10 to avoid token overload
        prompt = build_content_rewrite_prompt(
            industry=industry,
            content_type="service",
            original_content=service,
            company_name=company_name,
            brand_tone=brand_tone,
        )

        llm = get_llm_client()
        try:
            response = await llm.generate_text(prompt=prompt, max_tokens=50)
            rewritten = response.strip().strip('"').strip("'")

            rewritten_services.append(
                {
                    "original": service,
                    "rewritten": rewritten,
                    "type": "service",
                    "confidence": 80,
                }
            )
        except Exception as e:
            logger.warning(f"Service rewrite failed for '{service}': {e}")
            rewritten_services.append(
                {
                    "original": service,
                    "rewritten": service,
                    "type": "service",
                    "confidence": 50,
                    "error": str(e),
                }
            )

    return rewritten_services


async def rewrite_cta(
    original: str,
    industry: str,
    company_name: str,
    brand_tone: str,
    context: str = "primary",  # "primary", "secondary", "footer"
) -> dict[str, Any]:
    """Generate compelling CTA copy."""

    prompt = build_content_rewrite_prompt(
        industry=industry,
        content_type="cta",
        original_content=f"{original} (context: {context})",
        company_name=company_name,
        brand_tone=brand_tone,
    )

    llm = get_llm_client()
    try:
        response = await llm.generate_text(prompt=prompt, max_tokens=50)
        rewritten = response.strip().strip('"').strip("'")

        # Ensure it's action-oriented
        if not any(
            word in rewritten.lower()
            for word in [
                "get",
                "start",
                "try",
                "book",
                "schedule",
                "contact",
                "view",
                "explore",
                "learn",
                "see",
                "discover",
            ]
        ):
            rewritten = "Get Started"  # Safe fallback

        return {
            "original": original,
            "rewritten": rewritten,
            "type": "cta",
            "context": context,
            "confidence": 85,
        }
    except Exception as e:
        logger.warning(f"CTA rewrite failed: {e}, using fallback")
        fallback = "Get Started" if context == "primary" else "Learn More"
        return {
            "original": original,
            "rewritten": fallback,
            "type": "cta",
            "context": context,
            "confidence": 50,
            "error": str(e),
        }


async def rewrite_body_content(
    original: str,
    industry: str,
    company_name: str,
    brand_tone: str,
    max_length: int = 300,
) -> dict[str, Any]:
    """Rewrite body content to be more concise and impactful."""

    # If original is already short, don't rewrite
    if len(original) < 100:
        return {
            "original": original,
            "rewritten": original,
            "type": "body",
            "confidence": 90,
            "reason": "already_concise",
        }

    prompt = build_content_rewrite_prompt(
        industry=industry,
        content_type="body",
        original_content=original[:1000],  # Limit input
        company_name=company_name,
        brand_tone=brand_tone,
    )

    llm = get_llm_client()
    try:
        response = await llm.generate_text(prompt=prompt, max_tokens=max_length)
        rewritten = response.strip()

        return {
            "original": original,
            "rewritten": rewritten,
            "type": "body",
            "confidence": 80,
            "reduction": round((1 - len(rewritten) / len(original)) * 100),
        }
    except Exception as e:
        logger.warning(f"Body rewrite failed: {e}, using original")
        return {
            "original": original,
            "rewritten": original,
            "type": "body",
            "confidence": 50,
            "error": str(e),
        }


async def rewrite_hero_section(
    hero_data: dict[str, Any],
    industry: str,
    company_name: str,
    mission: str,
    brand_tone: str,
) -> dict[str, Any]:
    """Rewrite complete hero section for maximum impact."""

    rewritten_hero = {}

    # Rewrite headline
    if "headline" in hero_data:
        headline_result = await rewrite_headline(
            original=hero_data["headline"],
            industry=industry,
            company_name=company_name,
            brand_tone=brand_tone,
        )
        rewritten_hero["headline"] = headline_result["rewritten"]
        rewritten_hero["headline_meta"] = headline_result

    # Rewrite subheadline
    if "subheadline" in hero_data:
        subheadline_result = await rewrite_subheadline(
            original=hero_data.get("subheadline", mission),
            industry=industry,
            company_name=company_name,
            brand_tone=brand_tone,
        )
        rewritten_hero["subheadline"] = subheadline_result["rewritten"]
        rewritten_hero["subheadline_meta"] = subheadline_result

    # Rewrite CTA
    if "cta" in hero_data:
        cta_result = await rewrite_cta(
            original=hero_data.get("cta", "Get Started"),
            industry=industry,
            company_name=company_name,
            brand_tone=brand_tone,
            context="primary",
        )
        rewritten_hero["cta"] = cta_result["rewritten"]
        rewritten_hero["cta_meta"] = cta_result

    rewritten_hero["original"] = hero_data
    rewritten_hero["industry"] = industry

    return rewritten_hero


async def rewrite_site_content(
    site_data: dict[str, Any],
    industry: str,
    company_name: str,
    mission: str,
    brand_tone: str,
) -> dict[str, Any]:
    """Rewrite all site content for consistency and impact."""

    rewritten = {
        "company_name": company_name,
        "industry": industry,
        "rewrites": [],
    }

    # Rewrite hero
    if "hero" in site_data:
        hero_rewrite = await rewrite_hero_section(
            hero_data=site_data["hero"],
            industry=industry,
            company_name=company_name,
            mission=mission,
            brand_tone=brand_tone,
        )
        rewritten["hero"] = hero_rewrite
        rewritten["rewrites"].append({"section": "hero", "items": len(hero_rewrite)})

    # Rewrite services
    if "services" in site_data and isinstance(site_data["services"], list):
        services_rewrite = await rewrite_services(
            services=site_data["services"],
            industry=industry,
            company_name=company_name,
            brand_tone=brand_tone,
        )
        rewritten["services"] = services_rewrite
        rewritten["rewrites"].append(
            {"section": "services", "items": len(services_rewrite)}
        )

    # Rewrite other CTAs
    if "ctas" in site_data:
        cta_rewrites = []
        for cta_data in site_data["ctas"]:
            cta_rewrite = await rewrite_cta(
                original=cta_data.get("text", "Learn More"),
                industry=industry,
                company_name=company_name,
                brand_tone=brand_tone,
                context=cta_data.get("context", "secondary"),
            )
            cta_rewrites.append(cta_rewrite)
        rewritten["ctas"] = cta_rewrites
        rewritten["rewrites"].append({"section": "ctas", "items": len(cta_rewrites)})

    return rewritten


def extract_rewrite_statistics(rewritten_data: dict[str, Any]) -> dict[str, Any]:
    """Extract statistics from rewritten content."""

    stats = {
        "total_rewrites": 0,
        "successful_rewrites": 0,
        "failed_rewrites": 0,
        "average_confidence": 0,
        "sections_rewritten": [],
    }

    if "rewrites" in rewritten_data:
        stats["sections_rewritten"] = [r["section"] for r in rewritten_data["rewrites"]]
        stats["total_rewrites"] = sum(r["items"] for r in rewritten_data["rewrites"])

    # Count successes/failures
    confidences = []
    for section in ["hero", "services", "ctas"]:
        if section in rewritten_data:
            section_data = rewritten_data[section]
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if isinstance(value, dict) and "confidence" in value:
                        confidences.append(value["confidence"])
                        if value["confidence"] >= 70:
                            stats["successful_rewrites"] += 1
                        else:
                            stats["failed_rewrites"] += 1
            elif isinstance(section_data, list):
                for item in section_data:
                    if isinstance(item, dict) and "confidence" in item:
                        confidences.append(item["confidence"])
                        if item["confidence"] >= 70:
                            stats["successful_rewrites"] += 1
                        else:
                            stats["failed_rewrites"] += 1

    if confidences:
        stats["average_confidence"] = round(sum(confidences) / len(confidences))

    return stats
