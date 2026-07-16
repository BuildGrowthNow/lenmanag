"""
Hero variant generation system - provides 12+ unique hero layouts beyond the 4 base templates.
Part of Phase 3: Visual Diversity implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, cast

logger = logging.getLogger(__name__)

HeroVariantType = Literal[
    "video_fullscreen",
    "animated_gradient",
    "split_asymmetric",
    "parallax_layers",
    "typographic_only",
    "product_screenshot",
    "carousel_hero",
    "diagonal_split",
    "blob_shapes",
    "grid_mosaic",
    "minimal_centered",
    "immersive_3d",
]


HERO_VARIANTS: dict[HeroVariantType, dict[str, Any]] = {
    "video_fullscreen": {
        "name": "Full-Screen Video",
        "description": "Full-screen video background with centered text overlay",
        "best_for": ["creative_agency", "tech", "entertainment", "fashion"],
        "requirements": ["video_url"],
        "layout": "fullscreen",
        "text_position": "center",
        "overlay_opacity": 0.5,
        "animation": "fade_in",
    },
    "animated_gradient": {
        "name": "Animated Mesh Gradient",
        "description": "Animated mesh gradient with large typographic headline",
        "best_for": ["saas", "tech", "creative_agency", "consulting"],
        "requirements": [],
        "layout": "centered",
        "text_position": "center",
        "background": "animated_mesh",
        "animation": "gradient_shift",
    },
    "split_asymmetric": {
        "name": "Asymmetric Split",
        "description": "Asymmetric split (60/40) with image on left, text on right",
        "best_for": ["consulting", "legal_finance", "real_estate", "health_wellness"],
        "requirements": ["hero_image"],
        "layout": "split",
        "split_ratio": "60/40",
        "text_position": "right",
        "animation": "slide_in",
    },
    "parallax_layers": {
        "name": "Multi-Layer Parallax",
        "description": "Multi-layer parallax effect with depth",
        "best_for": ["creative_agency", "tech", "education"],
        "requirements": ["background_layers"],
        "layout": "layered",
        "text_position": "center",
        "animation": "parallax",
    },
    "typographic_only": {
        "name": "Pure Typography",
        "description": "Pure typography (no images), 150px headline",
        "best_for": ["consulting", "legal_finance", "creative_agency"],
        "requirements": [],
        "layout": "centered",
        "text_position": "center",
        "headline_size": "150px",
        "animation": "text_reveal",
    },
    "product_screenshot": {
        "name": "Product Screenshot",
        "description": "Centered product screenshot with glass-morphic overlay",
        "best_for": ["saas", "tech", "ecommerce"],
        "requirements": ["product_image"],
        "layout": "centered",
        "text_position": "top",
        "image_style": "glassmorphic",
        "animation": "float",
    },
    "carousel_hero": {
        "name": "Auto-Rotating Carousel",
        "description": "Auto-rotating hero images with text overlay",
        "best_for": ["ecommerce_fashion", "real_estate", "hospitality"],
        "requirements": ["carousel_images"],
        "layout": "fullscreen",
        "text_position": "left",
        "animation": "carousel",
    },
    "diagonal_split": {
        "name": "Diagonal Split",
        "description": "Diagonal split layout (not horizontal/vertical)",
        "best_for": ["creative_agency", "tech", "education"],
        "requirements": ["hero_image"],
        "layout": "diagonal",
        "split_angle": 15,
        "text_position": "bottom_left",
        "animation": "slide_diagonal",
    },
    "blob_shapes": {
        "name": "Abstract Blob Shapes",
        "description": "Abstract blob shapes with gradient fills",
        "best_for": ["creative_agency", "saas", "education"],
        "requirements": [],
        "layout": "centered",
        "text_position": "center",
        "background": "animated_blobs",
        "animation": "blob_morph",
    },
    "grid_mosaic": {
        "name": "Grid Mosaic",
        "description": "Grid of small images forming mosaic",
        "best_for": ["creative_agency", "ecommerce_fashion", "hospitality"],
        "requirements": ["mosaic_images"],
        "layout": "grid",
        "grid_columns": 4,
        "text_position": "overlay_center",
        "animation": "grid_reveal",
    },
    "minimal_centered": {
        "name": "Minimal Centered",
        "description": "Minimal centered text with subtle animation",
        "best_for": ["consulting", "legal_finance", "luxury_brands"],
        "requirements": [],
        "layout": "centered",
        "text_position": "center",
        "style": "minimal",
        "animation": "subtle_fade",
    },
    "immersive_3d": {
        "name": "3D Immersive",
        "description": "3D element (Three.js scene) with text overlay",
        "best_for": ["creative_agency", "tech", "gaming"],
        "requirements": ["3d_scene_config"],
        "layout": "fullscreen",
        "text_position": "center",
        "background": "3d_canvas",
        "animation": "3d_rotation",
    },
}


def select_hero_variant(
    industry: str,
    has_video: bool = False,
    has_product_image: bool = False,
    has_multiple_images: bool = False,
    brand_personality: str = "professional",
) -> tuple[HeroVariantType, dict[str, Any]]:
    """
    Select the best hero variant based on industry, available assets, and brand personality.

    Args:
        industry: Detected industry (e.g., "creative_agency", "saas")
        has_video: Whether the source site has video content
        has_product_image: Whether there's a product screenshot available
        has_multiple_images: Whether multiple hero images are available
        brand_personality: "bold", "minimal", "creative", "professional"

    Returns:
        Tuple of (variant_key, variant_config)
    """

    # Priority 1: Asset-driven selection
    if has_video:
        return "video_fullscreen", HERO_VARIANTS["video_fullscreen"]

    if has_product_image and industry in ["saas", "tech", "ecommerce"]:
        return "product_screenshot", HERO_VARIANTS["product_screenshot"]

    if has_multiple_images and industry in [
        "ecommerce_fashion",
        "real_estate",
        "hospitality",
    ]:
        return "carousel_hero", HERO_VARIANTS["carousel_hero"]

    # Priority 2: Industry-driven selection
    industry_preferences: dict[str, list[HeroVariantType]] = {
        "creative_agency": [
            "animated_gradient",
            "blob_shapes",
            "parallax_layers",
            "diagonal_split",
        ],
        "saas": ["animated_gradient", "product_screenshot", "minimal_centered"],
        "legal_finance": ["split_asymmetric", "typographic_only", "minimal_centered"],
        "consulting": ["split_asymmetric", "typographic_only", "minimal_centered"],
        "ecommerce_fashion": ["carousel_hero", "grid_mosaic", "minimal_centered"],
        "tech": ["animated_gradient", "parallax_layers", "product_screenshot"],
        "real_estate": ["carousel_hero", "split_asymmetric", "parallax_layers"],
        "health_wellness": [
            "split_asymmetric",
            "minimal_centered",
            "animated_gradient",
        ],
        "education": ["parallax_layers", "blob_shapes", "split_asymmetric"],
        "hospitality": ["carousel_hero", "grid_mosaic", "parallax_layers"],
    }

    # Priority 3: Brand personality adjustment
    personality_preferences: dict[str, list[HeroVariantType]] = {
        "bold": [
            "animated_gradient",
            "video_fullscreen",
            "blob_shapes",
            "diagonal_split",
        ],
        "minimal": ["minimal_centered", "typographic_only", "split_asymmetric"],
        "creative": [
            "blob_shapes",
            "parallax_layers",
            "immersive_3d",
            "diagonal_split",
        ],
        "professional": ["split_asymmetric", "typographic_only", "minimal_centered"],
    }

    # Get industry preferences
    industry_variants = industry_preferences.get(
        industry, ["minimal_centered", "split_asymmetric"]
    )

    # Filter by brand personality if provided
    selected_key: HeroVariantType = "minimal_centered"
    if brand_personality in personality_preferences:
        personality_variants = personality_preferences[brand_personality]
        # Find intersection of industry and personality preferences
        matching_variants = [v for v in industry_variants if v in personality_variants]
        if matching_variants:
            selected_key = cast(HeroVariantType, matching_variants[0])
        else:
            # Fallback to industry preference
            selected_key = cast(HeroVariantType, industry_variants[0])
    else:
        selected_key = cast(HeroVariantType, industry_variants[0])

    logger.info(
        f"Selected hero variant '{selected_key}' for industry={industry}, "
        f"personality={brand_personality}, has_video={has_video}"
    )

    return selected_key, HERO_VARIANTS[selected_key]


def generate_hero_config(
    variant_key: HeroVariantType,
    headline: str,
    subheadline: str,
    cta_text: str,
    cta_href: str,
    colors: dict[str, str],
    assets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a complete hero configuration for the selected variant.

    Args:
        variant_key: The hero variant type
        headline: Hero headline text
        subheadline: Hero subheadline text
        cta_text: CTA button text
        cta_href: CTA button href
        colors: Color system dictionary
        assets: Optional assets (video_url, images, etc.)

    Returns:
        Complete hero configuration dictionary
    """
    variant = HERO_VARIANTS[variant_key]
    assets = assets or {}

    base_config = {
        "variant": variant_key,
        "headline": headline,
        "subheadline": subheadline,
        "cta": {
            "text": cta_text,
            "href": cta_href,
        },
        "layout": variant["layout"],
        "text_position": variant["text_position"],
        "animation": variant["animation"],
        "colors": {
            "background": colors.get("surface", "#000000"),
            "text": colors.get("text", "#ffffff"),
            "accent": colors.get("primary", "#3b82f6"),
            "gradient_start": colors.get(
                "gradient_start", colors.get("primary", "#3b82f6")
            ),
            "gradient_end": colors.get(
                "gradient_end", colors.get("secondary", "#8b5cf6")
            ),
        },
    }

    # Add variant-specific configuration
    if variant_key == "video_fullscreen":
        base_config["video"] = {
            "url": assets.get("video_url", ""),
            "poster": assets.get("poster_url", ""),
            "overlay_opacity": variant["overlay_opacity"],
        }

    elif variant_key == "animated_gradient":
        base_config["gradient"] = {
            "type": "mesh",
            "colors": [
                colors.get("primary", "#3b82f6"),
                colors.get("secondary", "#8b5cf6"),
                colors.get("accent", "#ec4899"),
            ],
            "animated": True,
        }

    elif variant_key in ["split_asymmetric", "diagonal_split"]:
        base_config["image"] = {
            "url": assets.get("hero_image", ""),
            "alt": assets.get("image_alt", "Hero image"),
        }
        if variant_key == "split_asymmetric":
            base_config["split_ratio"] = variant["split_ratio"]
        else:
            base_config["split_angle"] = variant["split_angle"]

    elif variant_key == "parallax_layers":
        base_config["layers"] = assets.get(
            "layers",
            [
                {"speed": 0.5, "image": assets.get("layer_1", "")},
                {"speed": 0.3, "image": assets.get("layer_2", "")},
                {"speed": 0.1, "image": assets.get("layer_3", "")},
            ],
        )

    elif variant_key == "typographic_only":
        base_config["headline_size"] = variant["headline_size"]
        base_config["typographic_style"] = "bold"

    elif variant_key == "product_screenshot":
        base_config["product"] = {
            "image": assets.get("product_image", ""),
            "style": variant["image_style"],
        }

    elif variant_key == "carousel_hero":
        base_config["carousel"] = {
            "images": assets.get("carousel_images", []),
            "autoplay": True,
            "interval": 5000,
        }

    elif variant_key == "blob_shapes":
        base_config["blobs"] = {
            "count": 3,
            "colors": [
                colors.get("primary", "#3b82f6"),
                colors.get("secondary", "#8b5cf6"),
                colors.get("accent", "#ec4899"),
            ],
            "animated": True,
        }

    elif variant_key == "grid_mosaic":
        base_config["grid"] = {
            "images": assets.get("mosaic_images", []),
            "columns": variant["grid_columns"],
        }

    elif variant_key == "minimal_centered":
        base_config["style"] = "minimal"

    elif variant_key == "immersive_3d":
        base_config["scene_3d"] = assets.get(
            "3d_scene_config",
            {
                "type": "rotating_shapes",
                "primary_color": colors.get("primary", "#3b82f6"),
            },
        )

    return base_config


def get_fallback_hero_variant(theme_family: str) -> HeroVariantType:
    """
    Get a fallback hero variant based on the theme family if selection fails.

    Args:
        theme_family: The theme family (split-editorial, stacked-panel, media-led, centered-luxe)

    Returns:
        A safe fallback hero variant
    """
    fallback_map: dict[str, HeroVariantType] = {
        "split-editorial": "split_asymmetric",
        "stacked-panel": "minimal_centered",
        "media-led": "animated_gradient",
        "centered-luxe": "typographic_only",
    }

    return fallback_map.get(theme_family, "minimal_centered")
