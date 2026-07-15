"""
Industry Detection

Detects industry/vertical from extraction data to enable industry-specific design prompts.
"""

from __future__ import annotations

import re
from typing import Literal

IndustryType = Literal[
    "creative_agency",
    "saas",
    "legal_finance",
    "ecommerce_fashion",
    "consulting",
    "real_estate",
    "health_wellness",
    "tech",
    "education",
    "hospitality",
]


# Industry keyword patterns (weighted scoring)
INDUSTRY_PATTERNS = {
    "creative_agency": {
        "high_weight": [
            "design studio",
            "creative agency",
            "digital agency",
            "branding",
            "portfolio",
            "case studies",
            "our work",
            "projects",
            "creative",
            "campaigns",
        ],
        "medium_weight": [
            "design",
            "creative",
            "brand",
            "marketing",
            "advertising",
            "content creation",
        ],
    },
    "saas": {
        "high_weight": [
            "software",
            "platform",
            "saas",
            "dashboard",
            "integration",
            "api",
            "pricing plans",
            "free trial",
            "sign up",
            "demo",
        ],
        "medium_weight": [
            "cloud",
            "automation",
            "analytics",
            "workflow",
            "collaboration",
            "productivity",
        ],
    },
    "legal_finance": {
        "high_weight": [
            "law firm",
            "attorney",
            "legal services",
            "financial advisor",
            "investment",
            "accounting",
            "tax",
            "practice areas",
            "litigation",
        ],
        "medium_weight": [
            "legal",
            "finance",
            "compliance",
            "regulatory",
            "counsel",
            "consultation",
        ],
    },
    "ecommerce_fashion": {
        "high_weight": [
            "shop",
            "store",
            "collection",
            "new arrivals",
            "add to cart",
            "lookbook",
            "fashion",
            "clothing",
            "accessories",
        ],
        "medium_weight": [
            "products",
            "buy",
            "sale",
            "seasonal",
            "style",
            "wardrobe",
        ],
    },
    "consulting": {
        "high_weight": [
            "consulting",
            "strategy",
            "advisory",
            "business consulting",
            "management consulting",
            "transformation",
            "expertise",
        ],
        "medium_weight": [
            "solutions",
            "optimize",
            "improve",
            "growth",
            "efficiency",
            "insights",
        ],
    },
    "real_estate": {
        "high_weight": [
            "real estate",
            "properties",
            "listings",
            "homes for sale",
            "commercial real estate",
            "residential",
            "agent",
            "broker",
        ],
        "medium_weight": [
            "property",
            "buy",
            "sell",
            "rent",
            "lease",
            "location",
        ],
    },
    "health_wellness": {
        "high_weight": [
            "health",
            "wellness",
            "medical",
            "healthcare",
            "clinic",
            "treatment",
            "therapy",
            "fitness",
            "nutrition",
        ],
        "medium_weight": [
            "care",
            "healthy",
            "patient",
            "doctor",
            "specialist",
            "wellbeing",
        ],
    },
    "tech": {
        "high_weight": [
            "technology",
            "software development",
            "engineering",
            "innovation",
            "ai",
            "machine learning",
            "blockchain",
            "infrastructure",
        ],
        "medium_weight": [
            "tech",
            "digital",
            "development",
            "solution",
            "platform",
            "system",
        ],
    },
    "education": {
        "high_weight": [
            "education",
            "learning",
            "courses",
            "training",
            "academy",
            "school",
            "university",
            "certification",
        ],
        "medium_weight": [
            "teach",
            "student",
            "curriculum",
            "program",
            "workshop",
            "skills",
        ],
    },
    "hospitality": {
        "high_weight": [
            "hotel",
            "restaurant",
            "hospitality",
            "booking",
            "reservations",
            "venue",
            "catering",
            "events",
        ],
        "medium_weight": [
            "food",
            "dining",
            "stay",
            "accommodation",
            "guest",
            "service",
        ],
    },
}


def detect_industry(
    company_name: str = "",
    mission: str = "",
    services: list[str] | None = None,
    content_snippets: list[str] | None = None,
) -> tuple[IndustryType, float]:
    """
    Detect industry from extraction data using keyword scoring.

    Args:
        company_name: Company name
        mission: Mission statement or tagline
        services: List of service names
        content_snippets: List of content text snippets from the site

    Returns:
        Tuple of (industry_type, confidence_score)
    """
    services = services or []
    content_snippets = content_snippets or []

    # Combine all text for analysis
    all_text = " ".join(
        [
            company_name.lower(),
            mission.lower(),
            *[s.lower() for s in services],
            *[c.lower() for c in content_snippets],
        ]
    )

    scores: dict[IndustryType, float] = {
        "creative_agency": 0.0,
        "saas": 0.0,
        "legal_finance": 0.0,
        "ecommerce_fashion": 0.0,
        "consulting": 0.0,
        "real_estate": 0.0,
        "health_wellness": 0.0,
        "tech": 0.0,
        "education": 0.0,
        "hospitality": 0.0,
    }

    # Score each industry
    for industry, patterns in INDUSTRY_PATTERNS.items():
        score = 0.0

        # High weight keywords
        for keyword in patterns.get("high_weight", []):
            if keyword in all_text:
                score += 3.0

        # Medium weight keywords
        for keyword in patterns.get("medium_weight", []):
            if keyword in all_text:
                score += 1.0

        scores[industry] = score  # type: ignore

    # Find best match
    best_industry = max(scores.items(), key=lambda x: x[1])

    # Default to "tech" if no clear match
    if best_industry[1] < 1.0:
        return "tech", 0.3

    # Normalize confidence score (0-1)
    max_possible = 10.0  # Reasonable upper bound
    confidence = min(1.0, best_industry[1] / max_possible)

    return best_industry[0], confidence  # type: ignore


def get_industry_design_config(industry: IndustryType) -> dict:
    """
    Get design configuration for a specific industry.

    Returns design guidance including hero style, color palette direction,
    typography, and unique sections.
    """
    configs = {
        "creative_agency": {
            "visual_direction": "Bold, experimental, portfolio-first. Large typography, case study showcases, interactive elements.",
            "hero_style": "video_fullscreen",
            "color_palette_mood": "vibrant",
            "typography_pairing": "Display serif for headlines + clean sans for body",
            "unique_sections": [
                "portfolio_grid",
                "case_study",
                "awards_press",
                "team_showcase",
            ],
            "animation_intensity": "high",
            "dark_mode_default": True,
        },
        "saas": {
            "visual_direction": "Clean, functional, data-driven. Clear hierarchy, product screenshots, pricing comparison.",
            "hero_style": "product_screenshot",
            "color_palette_mood": "professional",
            "typography_pairing": "Geometric sans (Inter, Satoshi) throughout",
            "unique_sections": [
                "feature_comparison",
                "pricing_tiers",
                "integration_logos",
                "live_metrics",
            ],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
        "legal_finance": {
            "visual_direction": "Authoritative, professional, editorial. Strong typography, case results, trust signals.",
            "hero_style": "split_asymmetric",
            "color_palette_mood": "professional",
            "typography_pairing": "Serif display (Tiempos, Crimson) + sans body (Inter)",
            "unique_sections": [
                "practice_areas",
                "notable_cases",
                "team_credentials",
                "testimonials",
            ],
            "animation_intensity": "low",
            "dark_mode_default": False,
        },
        "ecommerce_fashion": {
            "visual_direction": "Visual-first, immersive, product photography. Large images, minimal text.",
            "hero_style": "carousel_hero",
            "color_palette_mood": "minimal",
            "typography_pairing": "Minimalist sans (Helvetica, Futura)",
            "unique_sections": [
                "lookbook_grid",
                "product_carousel",
                "instagram_feed",
                "size_guide",
            ],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
        "consulting": {
            "visual_direction": "Professional, strategic, results-focused. Data visualization, case studies, expertise signals.",
            "hero_style": "split_asymmetric",
            "color_palette_mood": "professional",
            "typography_pairing": "Geometric sans + neutral sans",
            "unique_sections": [
                "services_grid",
                "case_studies",
                "methodology",
                "insights",
            ],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
        "real_estate": {
            "visual_direction": "Clean, aspirational, property-focused. High-quality photography, map integration, listings.",
            "hero_style": "parallax_layers",
            "color_palette_mood": "calm",
            "typography_pairing": "Serif display + clean sans",
            "unique_sections": [
                "featured_properties",
                "neighborhood_guide",
                "agent_profiles",
                "testimonials",
            ],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
        "health_wellness": {
            "visual_direction": "Warm, trustworthy, human-centered. Soft colors, approachable imagery, clear information hierarchy.",
            "hero_style": "centered_with_image",
            "color_palette_mood": "calm",
            "typography_pairing": "Humanist sans throughout",
            "unique_sections": [
                "services_overview",
                "practitioner_bios",
                "patient_testimonials",
                "appointment_booking",
            ],
            "animation_intensity": "low",
            "dark_mode_default": False,
        },
        "tech": {
            "visual_direction": "Modern, innovative, technical. Abstract visuals, technical details, developer-focused.",
            "hero_style": "animated_gradient",
            "color_palette_mood": "bold",
            "typography_pairing": "Geometric sans + monospace accents",
            "unique_sections": [
                "technology_stack",
                "use_cases",
                "documentation",
                "developer_resources",
            ],
            "animation_intensity": "high",
            "dark_mode_default": True,
        },
        "education": {
            "visual_direction": "Accessible, structured, growth-oriented. Clear pathways, student success stories, course structure.",
            "hero_style": "split_asymmetric",
            "color_palette_mood": "vibrant",
            "typography_pairing": "Humanist sans + neutral sans",
            "unique_sections": [
                "course_catalog",
                "student_outcomes",
                "instructor_profiles",
                "enrollment_process",
            ],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
        "hospitality": {
            "visual_direction": "Inviting, experiential, atmosphere-focused. Rich imagery, menu highlights, booking flow.",
            "hero_style": "video_fullscreen",
            "color_palette_mood": "creative",
            "typography_pairing": "Display serif + clean sans",
            "unique_sections": [
                "menu_highlights",
                "photo_gallery",
                "reservations",
                "location_hours",
            ],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
    }

    return configs.get(
        industry,
        {
            "visual_direction": "Clean, modern, professional",
            "hero_style": "split_asymmetric",
            "color_palette_mood": "professional",
            "typography_pairing": "Geometric sans throughout",
            "unique_sections": ["services", "about", "contact"],
            "animation_intensity": "medium",
            "dark_mode_default": False,
        },
    )
