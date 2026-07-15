"""
Color System Generator

Generates full color systems from 1-3 source colors using color theory:
- Complementary colors (opposite on color wheel)
- Triadic colors (120° apart)
- Analogous colors (30° apart)
- Tints and shades (lighter/darker variants)
- Gradients (linear, radial, mesh)
"""

from __future__ import annotations

import colorsys
import re
from typing import Literal


def parse_hex_color(hex_color: str) -> tuple[float, float, float]:
    """Parse hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return r / 255.0, g / 255.0, b / 255.0


def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB (0-1 range) to hex color."""
    r_int = max(0, min(255, int(r * 255)))
    g_int = max(0, min(255, int(g * 255)))
    b_int = max(0, min(255, int(b * 255)))
    return f"#{r_int:02x}{g_int:02x}{b_int:02x}"


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL to hex color."""
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(r, g, b)


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color to HSL."""
    r, g, b = parse_hex_color(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def tint(hex_color: str, amount: float) -> str:
    """Lighten a color by mixing with white."""
    r, g, b = parse_hex_color(hex_color)
    r = r + (1 - r) * amount
    g = g + (1 - g) * amount
    b = b + (1 - b) * amount
    return rgb_to_hex(r, g, b)


def shade(hex_color: str, amount: float) -> str:
    """Darken a color by mixing with black."""
    r, g, b = parse_hex_color(hex_color)
    r = r * (1 - amount)
    g = g * (1 - amount)
    b = b * (1 - amount)
    return rgb_to_hex(r, g, b)


def saturate(hex_color: str, amount: float) -> str:
    """Increase saturation of a color."""
    h, s, l = hex_to_hsl(hex_color)
    s = min(1.0, s * amount)
    return hsl_to_hex(h, s, l)


def desaturate(hex_color: str, amount: float) -> str:
    """Decrease saturation of a color."""
    h, s, l = hex_to_hsl(hex_color)
    s = max(0.0, s * (1 - amount))
    return hsl_to_hex(h, s, l)


def complementary(hex_color: str) -> str:
    """Get complementary color (180° opposite on color wheel)."""
    h, s, l = hex_to_hsl(hex_color)
    h = (h + 0.5) % 1.0
    return hsl_to_hex(h, s, l)


def triadic(hex_color: str) -> tuple[str, str]:
    """Get triadic colors (120° apart on color wheel)."""
    h, s, l = hex_to_hsl(hex_color)
    h1 = (h + 1 / 3) % 1.0
    h2 = (h + 2 / 3) % 1.0
    return hsl_to_hex(h1, s, l), hsl_to_hex(h2, s, l)


def analogous(hex_color: str, degrees: int = 30) -> tuple[str, str]:
    """Get analogous colors (adjacent on color wheel)."""
    h, s, l = hex_to_hsl(hex_color)
    shift = degrees / 360.0
    h1 = (h + shift) % 1.0
    h2 = (h - shift) % 1.0
    return hsl_to_hex(h1, s, l), hsl_to_hex(h2, s, l)


def split_complementary(hex_color: str) -> tuple[str, str]:
    """Get split-complementary colors (150° apart)."""
    h, s, l = hex_to_hsl(hex_color)
    h1 = (h + 150 / 360) % 1.0
    h2 = (h + 210 / 360) % 1.0
    return hsl_to_hex(h1, s, l), hsl_to_hex(h2, s, l)


def adjust_lightness(hex_color: str, target_lightness: float) -> str:
    """Adjust color to a specific lightness value."""
    h, s, _ = hex_to_hsl(hex_color)
    return hsl_to_hex(h, s, target_lightness)


def alpha_blend(hex_color: str, alpha: float) -> str:
    """Simulate alpha by blending with white."""
    return tint(hex_color, 1 - alpha)


def generate_mesh_gradient(
    color1: str, color2: str, color3: str | None = None
) -> dict[str, str]:
    """Generate a mesh gradient configuration."""
    if color3 is None:
        color3 = analogous(color1, 45)[0]

    return {
        "type": "mesh",
        "colors": [color1, color2, color3],
        "positions": ["0% 0%", "100% 0%", "50% 100%"],
    }


MoodType = Literal["bold", "calm", "vibrant", "professional", "minimal", "creative"]


def get_base_surface(mood: MoodType, dark_mode: bool = True) -> str:
    """Get base surface color based on mood."""
    if dark_mode:
        mood_surfaces = {
            "bold": "#0a0a0a",
            "calm": "#18181b",
            "vibrant": "#0f0f0f",
            "professional": "#1a1a1a",
            "minimal": "#000000",
            "creative": "#0d0d0d",
        }
    else:
        mood_surfaces = {
            "bold": "#ffffff",
            "calm": "#f8f9fa",
            "vibrant": "#fefefe",
            "professional": "#f5f5f5",
            "minimal": "#ffffff",
            "creative": "#fafafa",
        }
    return mood_surfaces.get(mood, "#18181b" if dark_mode else "#ffffff")


def get_text_color(mood: MoodType, dark_mode: bool = True) -> str:
    """Get text color based on mood."""
    if dark_mode:
        return "#f4f4f5"
    return "#18181b"


IndustryType = Literal[
    "creative_agency",
    "saas",
    "legal_finance",
    "ecommerce_fashion",
    "consulting",
    "real_estate",
    "health_wellness",
    "tech",
]


def industry_default_color(industry: IndustryType) -> str:
    """Get default primary color for industry if no source colors available."""
    industry_colors = {
        "creative_agency": "#00ffff",  # cyan
        "saas": "#6366f1",  # indigo
        "legal_finance": "#1e40af",  # navy blue
        "ecommerce_fashion": "#000000",  # black
        "consulting": "#0f172a",  # slate
        "real_estate": "#059669",  # emerald
        "health_wellness": "#10b981",  # green
        "tech": "#8b5cf6",  # purple
    }
    return industry_colors.get(industry, "#6366f1")


def generate_color_system(
    source_colors: list[str],
    industry: IndustryType = "saas",
    mood: MoodType = "professional",
    dark_mode: bool = True,
) -> dict[str, str | dict]:
    """
    Generate a full 12+ color system from 1-3 source colors.

    Args:
        source_colors: List of 1-3 hex colors from source site
        industry: Industry type for defaults
        mood: Design mood/feeling
        dark_mode: Whether to generate for dark mode

    Returns:
        Dictionary with full color system including gradients
    """
    # Use first source color or industry default
    primary = source_colors[0] if source_colors else industry_default_color(industry)

    # Ensure primary has good saturation
    h, s, l = hex_to_hsl(primary)
    if s < 0.3:
        # Boost saturation for muted colors
        primary = hsl_to_hex(h, min(0.5, s + 0.2), l)

    # Generate secondary from complementary
    secondary = complementary(primary)

    # Generate accent from triadic
    accent_options = triadic(primary)
    accent = accent_options[0]

    # Adjust accent based on mood
    if mood == "vibrant":
        accent = saturate(accent, 1.3)
    elif mood == "calm":
        accent = desaturate(accent, 0.3)

    # Generate tints and shades
    primary_light = tint(primary, 0.3)
    primary_lighter = tint(primary, 0.5)
    primary_dark = shade(primary, 0.3)
    primary_darker = shade(primary, 0.5)

    # Generate accent variations
    accent_vibrant = saturate(accent, 1.2)
    accent_subtle = alpha_blend(accent, 0.15)

    # Analogous colors for gradients
    analog_colors = analogous(primary, 30)
    gradient_end = analog_colors[0]

    # Surface and text colors
    surface = get_base_surface(mood, dark_mode)
    text = get_text_color(mood, dark_mode)

    # Border color (primary with low opacity)
    h, s, l = hex_to_hsl(primary)
    border = hsl_to_hex(h, s * 0.5, 0.3 if dark_mode else 0.8)

    # Mesh gradient
    mesh = generate_mesh_gradient(primary, accent, gradient_end)

    return {
        # Core colors
        "primary": primary,
        "primary_light": primary_light,
        "primary_lighter": primary_lighter,
        "primary_dark": primary_dark,
        "primary_darker": primary_darker,
        "secondary": secondary,
        "accent": accent,
        "accent_vibrant": accent_vibrant,
        "accent_subtle": accent_subtle,

        # Gradient colors
        "gradient_start": primary,
        "gradient_end": gradient_end,
        "mesh_gradient": mesh,

        # Base colors
        "surface": surface,
        "text": text,
        "border": border,

        # Semantic colors
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "info": accent,

        # Metadata
        "mood": mood,
        "dark_mode": dark_mode,
        "industry": industry,
    }


def generate_css_variables(color_system: dict[str, str | dict]) -> str:
    """Generate CSS variables from color system."""
    lines = [":root {"]

    for key, value in color_system.items():
        if isinstance(value, str) and value.startswith("#"):
            css_var = key.replace("_", "-")
            lines.append(f"  --color-{css_var}: {value};")

    lines.append("}")
    return "\n".join(lines)


def generate_tailwind_colors(color_system: dict[str, str | dict]) -> dict[str, str]:
    """Generate Tailwind color configuration."""
    colors = {}

    for key, value in color_system.items():
        if isinstance(value, str) and value.startswith("#"):
            tailwind_key = key.replace("_", "-")
            colors[tailwind_key] = value

    return colors
