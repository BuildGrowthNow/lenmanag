"""
Creative Copy Generation

Generate multiple creative variations for headlines and CTAs,
then select the best one based on industry and brand.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


# Industry-specific power verbs
POWER_VERBS = {
    "creative_agency": [
        "Transform",
        "Craft",
        "Architect",
        "Unleash",
        "Amplify",
        "Design",
        "Build",
        "Shape",
        "Create",
        "Elevate",
    ],
    "saas": [
        "Accelerate",
        "Automate",
        "Streamline",
        "Scale",
        "Deploy",
        "Ship",
        "Build",
        "Launch",
        "Optimize",
        "Power",
    ],
    "legal_finance": [
        "Protect",
        "Defend",
        "Navigate",
        "Secure",
        "Resolve",
        "Counsel",
        "Advise",
        "Guide",
        "Advocate",
        "Represent",
    ],
    "ecommerce_fashion": [
        "Discover",
        "Shop",
        "Explore",
        "Style",
        "Curate",
        "Find",
        "Wear",
        "Express",
        "Elevate",
        "Own",
    ],
    "consulting": [
        "Transform",
        "Optimize",
        "Accelerate",
        "Navigate",
        "Drive",
        "Deliver",
        "Solve",
        "Improve",
        "Scale",
        "Execute",
    ],
    "real_estate": [
        "Discover",
        "Find",
        "Explore",
        "Invest",
        "Own",
        "Build",
        "Secure",
        "Live",
        "Grow",
        "Unlock",
    ],
    "health_wellness": [
        "Heal",
        "Restore",
        "Improve",
        "Transform",
        "Strengthen",
        "Balance",
        "Thrive",
        "Recover",
        "Optimize",
        "Care",
    ],
    "tech": [
        "Build",
        "Deploy",
        "Scale",
        "Ship",
        "Launch",
        "Innovate",
        "Engineer",
        "Power",
        "Accelerate",
        "Transform",
    ],
}


def get_power_verbs(industry: str) -> list[str]:
    """Get power verbs for an industry."""
    return POWER_VERBS.get(industry, POWER_VERBS["saas"])


def generate_headline_variations(
    company_name: str,
    mission: str,
    industry: str,
    positioning: str = "",
) -> list[dict[str, Any]]:
    """Generate multiple headline variations using templates."""

    power_verbs = get_power_verbs(industry)
    variations = []

    # Extract key benefit/outcome from mission
    # Simple heuristic: look for "we help/we build/we create" patterns
    benefit = mission.lower()
    for phrase in ["we help", "we build", "we create", "we provide", "we offer"]:
        if phrase in benefit:
            benefit = benefit.split(phrase, 1)[1].strip()
            break

    # Clean up benefit
    benefit = benefit.strip().rstrip(".")
    if len(benefit) > 80:
        benefit = benefit[:77] + "..."

    # Template 1: Power Verb + Benefit
    if benefit:
        variations.append({
            "headline": f"{power_verbs[0]} {benefit}",
            "template": "verb_benefit",
            "confidence": 85,
        })

    # Template 2: Company Name + Value Prop
    variations.append({
        "headline": f"{company_name}: {mission[:60]}",
        "template": "name_mission",
        "confidence": 75,
    })

    # Template 3: Bold Statement (industry-specific)
    industry_statements = {
        "creative_agency": "Digital experiences that convert",
        "saas": "Ship faster. Scale effortlessly.",
        "legal_finance": "Proven expertise. Trusted counsel.",
        "ecommerce_fashion": "Style. Refined.",
        "consulting": "Strategy. Execution. Results.",
        "real_estate": "Your next home awaits",
        "health_wellness": "Your health, optimized",
        "tech": "Build the future",
    }

    statement = industry_statements.get(industry, "Excellence, delivered")
    variations.append({
        "headline": statement,
        "template": "bold_statement",
        "confidence": 70,
    })

    # Template 4: We [Power Verb] pattern
    if power_verbs:
        variations.append({
            "headline": f"We {power_verbs[0].lower()} {benefit}" if benefit else f"We {power_verbs[0].lower()} what others can't",
            "template": "we_verb",
            "confidence": 80,
        })

    # Template 5: Outcome-focused
    outcome_templates = {
        "creative_agency": "From concept to conversion",
        "saas": "10x your productivity",
        "legal_finance": "Protecting your interests since [year]",
        "ecommerce_fashion": "Wardrobe essentials, elevated",
        "consulting": "Transform your business",
        "real_estate": "Find your dream home",
        "health_wellness": "Feel your best",
        "tech": "Infrastructure that scales",
    }

    variations.append({
        "headline": outcome_templates.get(industry, "Results you can measure"),
        "template": "outcome_focused",
        "confidence": 78,
    })

    # Add positioning if available
    if positioning and len(positioning) < 80:
        variations.append({
            "headline": positioning,
            "template": "positioning",
            "confidence": 82,
        })

    return variations


def generate_cta_variations(
    industry: str, context: str = "primary"
) -> list[dict[str, Any]]:
    """Generate CTA variations for an industry."""

    variations = []

    cta_patterns = {
        "creative_agency": {
            "primary": [
                "View Our Work",
                "Start a Project",
                "See Case Studies",
                "Let's Create Together",
                "Explore Our Portfolio",
            ],
            "secondary": [
                "Learn More",
                "Get in Touch",
                "Book a Call",
                "See Our Process",
            ],
            "footer": [
                "Start Your Project",
                "Contact Us",
                "Get a Quote",
            ],
        },
        "saas": {
            "primary": [
                "Start Free Trial",
                "Get Started Free",
                "Try It Now",
                "Start Building",
                "Sign Up Free",
            ],
            "secondary": [
                "Book a Demo",
                "See Pricing",
                "Watch Video",
                "Read Docs",
            ],
            "footer": [
                "Get Started",
                "Contact Sales",
                "View Plans",
            ],
        },
        "legal_finance": {
            "primary": [
                "Schedule Consultation",
                "Discuss Your Case",
                "Contact Our Team",
                "Get Legal Advice",
                "Book Appointment",
            ],
            "secondary": [
                "Learn More",
                "View Services",
                "Meet Our Team",
                "Read Insights",
            ],
            "footer": [
                "Contact Us",
                "Schedule Call",
                "Get Started",
            ],
        },
        "ecommerce_fashion": {
            "primary": [
                "Shop Now",
                "Shop the Collection",
                "Explore Styles",
                "Shop Women",
                "Shop Men",
            ],
            "secondary": [
                "Learn More",
                "View Lookbook",
                "Find Your Style",
                "Size Guide",
            ],
            "footer": [
                "Shop All",
                "New Arrivals",
                "Contact Us",
            ],
        },
        "consulting": {
            "primary": [
                "Start Your Transformation",
                "Schedule Consultation",
                "Discuss Your Needs",
                "Get Expert Advice",
                "Let's Talk",
            ],
            "secondary": [
                "Learn More",
                "View Services",
                "Read Case Studies",
                "See Our Approach",
            ],
            "footer": [
                "Get Started",
                "Contact Us",
                "Book a Call",
            ],
        },
        "real_estate": {
            "primary": [
                "Search Homes",
                "View Properties",
                "Find Your Home",
                "Start Your Search",
                "Explore Listings",
            ],
            "secondary": [
                "Learn More",
                "Meet Our Agents",
                "Book a Showing",
                "Get Pre-Approved",
            ],
            "footer": [
                "Contact Us",
                "View Listings",
                "Schedule Tour",
            ],
        },
        "health_wellness": {
            "primary": [
                "Book Appointment",
                "Schedule Consultation",
                "Get Started",
                "Contact Our Team",
                "Learn More",
            ],
            "secondary": [
                "View Services",
                "Meet Our Practitioners",
                "Read Patient Stories",
                "Insurance Info",
            ],
            "footer": [
                "Book Now",
                "Contact Us",
                "New Patients",
            ],
        },
        "tech": {
            "primary": [
                "Get Started",
                "Start Building",
                "Try for Free",
                "Read the Docs",
                "View on GitHub",
            ],
            "secondary": [
                "Learn More",
                "See Examples",
                "Join Discord",
                "Read Blog",
            ],
            "footer": [
                "Get Started",
                "Documentation",
                "Contact Sales",
            ],
        },
    }

    industry_ctas = cta_patterns.get(industry, cta_patterns["saas"])
    context_ctas = industry_ctas.get(context, industry_ctas["primary"])

    for i, cta in enumerate(context_ctas):
        variations.append({
            "text": cta,
            "context": context,
            "confidence": 90 - (i * 2),  # Slightly prefer earlier options
        })

    return variations


def select_best_headline(
    variations: list[dict[str, Any]],
    brand_tone: str = "",
    prefer_bold: bool = False,
) -> dict[str, Any]:
    """Select the best headline from variations based on criteria."""

    if not variations:
        return {"headline": "Welcome", "confidence": 50}

    # Scoring logic
    scored = []
    for var in variations:
        score = var.get("confidence", 70)

        # Adjust based on brand tone
        if brand_tone:
            tone_lower = brand_tone.lower()
            headline_lower = var["headline"].lower()

            if "professional" in tone_lower and var["template"] in [
                "name_mission",
                "positioning",
            ]:
                score += 5
            if "bold" in tone_lower and var["template"] == "bold_statement":
                score += 8
            if "friendly" in tone_lower and "we" in headline_lower:
                score += 5

        # Prefer shorter headlines
        if len(var["headline"]) < 50:
            score += 3

        # Penalize very long headlines
        if len(var["headline"]) > 80:
            score -= 10

        # Boost if prefer_bold is set
        if prefer_bold and var["template"] in ["bold_statement", "verb_benefit"]:
            score += 10

        scored.append({**var, "score": score})

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[0]


def select_best_cta(
    variations: list[dict[str, Any]], brand_tone: str = ""
) -> dict[str, Any]:
    """Select the best CTA from variations."""

    if not variations:
        return {"text": "Get Started", "confidence": 50, "context": "primary"}

    # For CTAs, we generally just take the first (highest confidence)
    # But we can add tone-based adjustments if needed

    scored = []
    for var in variations:
        score = var.get("confidence", 80)

        # Adjust based on brand tone
        if brand_tone:
            tone_lower = brand_tone.lower()
            text_lower = var["text"].lower()

            if "professional" in tone_lower and any(
                word in text_lower for word in ["schedule", "consultation", "contact"]
            ):
                score += 5

            if "casual" in tone_lower and any(
                word in text_lower for word in ["try", "start", "get"]
            ):
                score += 5

        scored.append({**var, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[0]


async def generate_creative_headline(
    company_name: str,
    mission: str,
    industry: str,
    brand_tone: str = "",
    positioning: str = "",
    prefer_bold: bool = False,
) -> dict[str, Any]:
    """Generate and select the best creative headline."""

    variations = generate_headline_variations(
        company_name=company_name,
        mission=mission,
        industry=industry,
        positioning=positioning,
    )

    best = select_best_headline(
        variations=variations, brand_tone=brand_tone, prefer_bold=prefer_bold
    )

    return {
        "headline": best["headline"],
        "template": best.get("template"),
        "confidence": best.get("confidence", 75),
        "variations_generated": len(variations),
        "method": "template_based",
    }


async def generate_creative_cta(
    industry: str, context: str = "primary", brand_tone: str = ""
) -> dict[str, Any]:
    """Generate and select the best CTA."""

    variations = generate_cta_variations(industry=industry, context=context)

    best = select_best_cta(variations=variations, brand_tone=brand_tone)

    return {
        "text": best["text"],
        "context": best.get("context", context),
        "confidence": best.get("confidence", 85),
        "variations_generated": len(variations),
        "method": "template_based",
    }
