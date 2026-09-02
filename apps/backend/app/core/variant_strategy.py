"""
Variant strategy definitions for HTML multi-variant generation.

Each variant type maps to a distinct creative direction with specific
design parameters to ensure meaningfully different outputs.
"""

from __future__ import annotations

from typing import TypedDict

from app.schemas.brief import DesignMode
from app.schemas.site import PaletteMode, VariantType


class VariantStrategy(TypedDict):
    """Strategy definition for a single variant."""

    variantType: VariantType
    variantLabel: str
    variantPosition: int
    designMode: DesignMode
    paletteMode: PaletteMode
    creativeBriefGuidance: str
    inspirationKeywords: list[str]
    avoidPatterns: list[str]


def get_variant_strategies(
    industry: str | None = None,
) -> dict[VariantType, VariantStrategy]:
    """
    Return variant strategies based on industry context.

    Each variant is designed to be DISTINCTLY DIFFERENT:
    - Variant 1: Industry-standard, professional, proven patterns
    - Variant 2: Bold, experimental, startup-like energy
    - Variant 3: Alternative approach (colorful, playful, or dark luxe)

    Args:
        industry: Optional industry context for tailoring strategies

    Returns:
        Dictionary mapping variant type to strategy definition
    """
    base_strategies: dict[VariantType, VariantStrategy] = {
        "html_v1": {
            "variantType": "html_v1",
            "variantLabel": "Professional Standard",
            "variantPosition": 1,
            "designMode": "corporate",
            "paletteMode": "zinc",
            "creativeBriefGuidance": """
                Generate a professional, industry-standard design:
                - Clean, structured layouts with clear visual hierarchy
                - Conservative color palette: neutrals (grays, whites) with single brand accent
                - Serif or elegant sans-serif typography for trust and authority
                - Light mode with spacious whitespace
                - Subtle animations, professional interactions
                - Focus on credibility, clarity, and user confidence
                - Editorial-style content presentation
            """,
            "inspirationKeywords": [
                "editorial",
                "professional",
                "structured",
                "trustworthy",
                "clean",
                "spacious",
                "authoritative",
                "premium",
            ],
            "avoidPatterns": [
                "experimental layouts",
                "bold colors",
                "playful shapes",
                "heavy animations",
                "dark mode",
                "trendy effects",
            ],
        },
        "html_v2": {
            "variantType": "html_v2",
            "variantLabel": "Bold Startup",
            "variantPosition": 2,
            "designMode": "interactive",
            "paletteMode": "colorful",
            "creativeBriefGuidance": """
                Generate a bold, high-energy startup aesthetic:
                - Asymmetric, experimental layouts with unexpected element placement
                - Dark mode with electric accent colors (neons, vibrant blues/purples)
                - Geometric sans-serif typography, large display headings
                - High contrast, dramatic color shifts
                - Expressive animations: parallax, scroll-triggered reveals, micro-interactions
                - Confident, punchy copy with strong CTAs
                - Modern tech/startup vibe with cutting-edge design patterns
            """,
            "inspirationKeywords": [
                "bold",
                "experimental",
                "high-energy",
                "asymmetric",
                "dark-mode",
                "neon-accents",
                "parallax",
                "startup",
                "confident",
                "modern",
                "cutting-edge",
            ],
            "avoidPatterns": [
                "conservative layouts",
                "light mode",
                "subtle colors",
                "serif fonts",
                "corporate stiffness",
                "traditional grids",
            ],
        },
        "html_v3": {
            "variantType": "html_v3",
            "variantLabel": "Creative Alternative",
            "variantPosition": 3,
            "designMode": "playful",
            "paletteMode": "colorful",
            "creativeBriefGuidance": """
                Generate a distinctive, creative alternative design:
                - Colorful, multi-hue palette (3-4 brand colors working together)
                - Playful, organic shapes and rounded elements
                - make sure that the animations and script of the animations work well
                - dont change the cursor design, keep it default   
                - Friendly, approachable tone with warm colors
                - Balanced energy: not corporate, not hyper-bold, but creative and memorable
                - Smooth, delightful animations (bounces, elastic easing)
                - Approachable copy, human voice
                - Unique visual personality that stands out from competitors
            """,
            "inspirationKeywords": [
                "colorful",
                "playful",
                "organic",
                "approachable",
                "creative",
                "distinctive",
                "warm",
                "friendly",
                "rounded",
                "delightful",
                "unique",
            ],
            "avoidPatterns": [
                "monochrome",
                "rigid grids",
                "corporate stiffness",
                "harsh contrasts",
                "cold colors",
                "generic stock photos",
            ],
        },
    }

    # Industry-specific adjustments
    industry_lower = (industry or "").lower()

    if any(
        keyword in industry_lower
        for keyword in ["consulting", "legal", "finance", "b2b"]
    ):
        # For professional services: make variant 3 more luxe/refined instead of playful
        base_strategies["html_v3"] = {
            "variantType": "html_v3",
            "variantLabel": "Minimal Luxe",
            "variantPosition": 3,
            "designMode": "minimalist",
            "paletteMode": "light",
            "creativeBriefGuidance": """
                Generate a premium, minimal luxury design:
                - Soft, refined color palette: neutrals with single elegant accent
                - Abundant whitespace, quiet confidence
                - Serif display typography with elegant sans body text
                - Light mode or soft dark mode (charcoal, not black)
                - Subtle, refined animations (fades, smooth reveals)
                - Premium, sophisticated tone
                - Focus on quality over quantity of elements
            """,
            "inspirationKeywords": [
                "minimal",
                "luxe",
                "refined",
                "premium",
                "elegant",
                "sophisticated",
                "quiet",
                "spacious",
                "quality",
            ],
            "avoidPatterns": [
                "busy layouts",
                "loud colors",
                "playful shapes",
                "excessive decoration",
                "generic templates",
            ],
        }

    if any(keyword in industry_lower for keyword in ("well", "water", "drilling")):
        base_strategies["html_v1"].update({"variantLabel": "Regional Trust", "paletteMode": "light", "creativeBriefGuidance": "Premium editorial direction built on real regional field imagery, heritage, trust and source-backed service information. Use a bright, grounded palette and a quiet reveal system.", "inspirationKeywords": ["regional", "editorial", "trust", "field photography", "heritage"], "avoidPatterns": ["startup", "neon", "generic svg art", "legal language"]})
        base_strategies["html_v2"].update({"variantLabel": "Field Precision", "paletteMode": "zinc", "creativeBriefGuidance": "Cinematic industrial direction: equipment and drilling photography, high-contrast but brand-grounded palette, technical precision and emergency response. Use one operational carousel or progress interaction.", "inspirationKeywords": ["cinematic", "industrial", "precision", "equipment", "water"], "avoidPatterns": ["purple gradient", "SaaS", "bento template", "random stock"]})
        base_strategies["html_v3"].update({"variantLabel": "Clean Water, Close to Home", "paletteMode": "light", "creativeBriefGuidance": "Warm community and clean-water direction with real people/location imagery, friendly but premium typography, a service-area story and gentle tactile motion.", "inspirationKeywords": ["community", "clean water", "warm", "craft", "local"], "avoidPatterns": ["playful blobs", "legal terminology", "fake metrics", "generic icons"]})
    elif any(keyword in industry_lower for keyword in ("trades", "home service")):
        base_strategies["html_v1"].update({"variantLabel": "Local Trust", "paletteMode": "light", "creativeBriefGuidance": "Premium editorial direction built on the approved service positioning, local credibility and clear customer guidance. Use a bright, grounded palette and a quiet reveal system.", "inspirationKeywords": ["local", "editorial", "trust", "service", "clear"], "avoidPatterns": ["startup", "neon", "generic svg art", "unverified claims"]})
        base_strategies["html_v2"].update({"variantLabel": "Service Precision", "paletteMode": "zinc", "creativeBriefGuidance": "Confident service direction with crisp hierarchy, practical proof and deliberate motion. Use high contrast and one useful operational interaction without inventing technical claims.", "inspirationKeywords": ["service", "precision", "confident", "structured", "action"], "avoidPatterns": ["purple gradient", "SaaS", "bento template", "random stock"]})
        base_strategies["html_v3"].update({"variantLabel": "Community Care", "paletteMode": "light", "creativeBriefGuidance": "Warm, human service direction with real source-backed imagery, friendly premium typography and a clear path to contact. Use gentle tactile motion and an approachable rhythm.", "inspirationKeywords": ["community", "warm", "service", "human", "local"], "avoidPatterns": ["playful blobs", "legal terminology", "fake metrics", "generic icons"]})

    return base_strategies


def get_variant_strategy(
    variant_type: VariantType, industry: str | None = None
) -> VariantStrategy:
    """Get strategy for a specific variant type."""
    strategies = get_variant_strategies(industry)
    if variant_type not in strategies:
        raise ValueError(f"Unknown variant type: {variant_type}")
    return strategies[variant_type]
