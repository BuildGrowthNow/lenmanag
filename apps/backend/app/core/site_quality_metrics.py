"""
Site Quality Metrics

Tools for measuring uniqueness and quality of generated sites.
Used for A/B testing and iteration on the design system.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def calculate_visual_similarity_score(
    site_a: dict[str, Any], site_b: dict[str, Any]
) -> float:
    """
    Calculate visual similarity between two generated sites.
    Returns a score from 0.0 (completely different) to 1.0 (identical).

    Uses a simplified perceptual hash approach based on design DNA.
    """

    # Extract design DNA components
    def extract_dna(site: dict[str, Any]) -> dict[str, Any]:
        return {
            "theme": site.get("themeName", ""),
            "hero_variant": site.get("heroVariant", ""),
            "palette_mode": site.get("paletteMode", ""),
            "primary_color": site.get("colors", {}).get("primary", ""),
            "secondary_color": site.get("colors", {}).get("secondary", ""),
            "font_family": site.get("typography", {}).get("fontFamily", ""),
            "section_count": len(site.get("sections", [])),
            "section_types": sorted(
                [s.get("kind", "") for s in site.get("sections", [])]
            ),
            "has_nav": bool(site.get("navigationConfig")),
            "nav_style": site.get("navigationConfig", {}).get("style", ""),
        }

    dna_a = extract_dna(site_a)
    dna_b = extract_dna(site_b)

    # Calculate similarity for each component
    similarities: list[float] = []

    # Theme (binary)
    similarities.append(1.0 if dna_a["theme"] == dna_b["theme"] else 0.0)

    # Hero variant (binary)
    similarities.append(1.0 if dna_a["hero_variant"] == dna_b["hero_variant"] else 0.0)

    # Palette mode (binary)
    similarities.append(1.0 if dna_a["palette_mode"] == dna_b["palette_mode"] else 0.0)

    # Colors (compare hex values with tolerance)
    color_sim = calculate_color_similarity(
        dna_a["primary_color"], dna_b["primary_color"]
    )
    similarities.append(color_sim)

    color_sim_2 = calculate_color_similarity(
        dna_a["secondary_color"], dna_b["secondary_color"]
    )
    similarities.append(color_sim_2)

    # Typography (binary)
    similarities.append(1.0 if dna_a["font_family"] == dna_b["font_family"] else 0.0)

    # Section structure (Jaccard similarity)
    section_sim = calculate_jaccard_similarity(
        dna_a["section_types"], dna_b["section_types"]
    )
    similarities.append(section_sim)

    # Navigation (binary)
    similarities.append(1.0 if dna_a["nav_style"] == dna_b["nav_style"] else 0.0)

    # Overall similarity (average of all components)
    overall_similarity = sum(similarities) / len(similarities)

    return round(overall_similarity, 3)


def calculate_color_similarity(hex_a: str, hex_b: str) -> float:
    """Calculate similarity between two hex colors (0.0 = different, 1.0 = identical)."""

    if not hex_a or not hex_b:
        return 0.0

    # Remove # prefix
    hex_a = hex_a.lstrip("#")
    hex_b = hex_b.lstrip("#")

    # Convert to RGB
    try:
        r1, g1, b1 = int(hex_a[0:2], 16), int(hex_a[2:4], 16), int(hex_a[4:6], 16)
        r2, g2, b2 = int(hex_b[0:2], 16), int(hex_b[2:4], 16), int(hex_b[4:6], 16)
    except (ValueError, IndexError):
        return 0.0

    # Calculate Euclidean distance in RGB space
    distance = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5

    # Normalize to 0-1 (max distance is ~441 for RGB)
    max_distance = (255**2 + 255**2 + 255**2) ** 0.5
    similarity = 1.0 - (distance / max_distance)

    return round(similarity, 3)


def calculate_jaccard_similarity(list_a: list[str], list_b: list[str]) -> float:
    """Calculate Jaccard similarity between two lists."""

    set_a = set(list_a)
    set_b = set(list_b)

    if not set_a and not set_b:
        return 1.0

    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return round(intersection / union, 3)


def measure_color_diversity(site: dict[str, Any]) -> dict[str, Any]:
    """Measure color diversity in a generated site."""

    colors = site.get("colors", {})

    # Count unique colors
    unique_colors = set()
    for value in colors.values():
        if isinstance(value, str) and value.startswith("#"):
            unique_colors.add(value.lower())

    color_count = len(unique_colors)

    # Check for mesh gradient
    has_mesh_gradient = "meshGradient" in colors or "gradientStart" in colors

    # Check for advanced color system
    has_advanced_colors = all(
        key in colors
        for key in ["primary", "secondary", "accent", "primaryLight", "primaryDark"]
    )

    return {
        "unique_color_count": color_count,
        "has_mesh_gradient": has_mesh_gradient,
        "has_advanced_colors": has_advanced_colors,
        "passes_diversity_threshold": color_count >= 8,
        "score": min(color_count / 12, 1.0),  # Target: 12+ colors
    }


def measure_animation_coverage(site: dict[str, Any]) -> dict[str, Any]:
    """Measure animation coverage in sections."""

    sections = site.get("sections", [])
    total_sections = len(sections)

    if total_sections == 0:
        return {"coverage": 0.0, "animated_sections": 0, "total_sections": 0}

    # Count sections with animation hints
    animated_sections = 0
    for section in sections:
        # Check for animation-related keys (this is heuristic)
        section_str = str(section).lower()
        has_animation = any(
            keyword in section_str
            for keyword in [
                "fade",
                "slide",
                "stagger",
                "reveal",
                "animate",
                "parallax",
                "hover",
            ]
        )
        if has_animation:
            animated_sections += 1

    coverage = animated_sections / total_sections

    return {
        "coverage": round(coverage, 3),
        "animated_sections": animated_sections,
        "total_sections": total_sections,
        "passes_threshold": coverage >= 0.8,
        "score": coverage,
    }


def measure_component_variety(site: dict[str, Any]) -> dict[str, Any]:
    """Measure variety of components used across sections."""

    sections = site.get("sections", [])

    if not sections:
        return {"variety_score": 0.0, "unique_components": 0, "total_sections": 0}

    # Extract component types (simplified heuristic)
    component_types = []
    for section in sections:
        kind = section.get("kind", "")
        # Check for specific component mentions
        section_str = str(section).lower()
        if "accordion" in section_str:
            component_types.append("accordion")
        if "carousel" in section_str:
            component_types.append("carousel")
        if "tabs" in section_str:
            component_types.append("tabs")
        if "grid" in section_str or "bento" in section_str:
            component_types.append("grid")
        if "comparison" in section_str or "table" in section_str:
            component_types.append("comparison")
        if kind:
            component_types.append(kind)

    unique_components = len(set(component_types))
    total_sections = len(sections)

    # Calculate variety score (avoid over-reuse)
    variety_score = unique_components / total_sections if total_sections > 0 else 0.0

    # Threshold: no more than 40% reuse
    passes_threshold = variety_score >= 0.6

    return {
        "variety_score": round(variety_score, 3),
        "unique_components": unique_components,
        "total_sections": total_sections,
        "passes_threshold": passes_threshold,
        "score": variety_score,
    }


def calculate_overall_quality_score(site: dict[str, Any]) -> dict[str, Any]:
    """Calculate overall quality score for a generated site."""

    color_metrics = measure_color_diversity(site)
    animation_metrics = measure_animation_coverage(site)
    component_metrics = measure_component_variety(site)

    # Weighted average of all metrics
    weights = {
        "color_diversity": 0.3,
        "animation_coverage": 0.35,
        "component_variety": 0.35,
    }

    overall_score = (
        color_metrics["score"] * weights["color_diversity"]
        + animation_metrics["score"] * weights["animation_coverage"]
        + component_metrics["score"] * weights["component_variety"]
    )

    return {
        "overall_score": round(overall_score, 3),
        "grade": _score_to_grade(overall_score),
        "metrics": {
            "color_diversity": color_metrics,
            "animation_coverage": animation_metrics,
            "component_variety": component_metrics,
        },
        "passes_quality_threshold": overall_score >= 0.75,
    }


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 0.9:
        return "A+"
    elif score >= 0.85:
        return "A"
    elif score >= 0.8:
        return "B+"
    elif score >= 0.75:
        return "B"
    elif score >= 0.7:
        return "C+"
    elif score >= 0.6:
        return "C"
    else:
        return "D"


def compare_site_batches(
    batch_a: list[dict[str, Any]], batch_b: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Compare two batches of generated sites (e.g., before/after system changes).
    Returns comparative metrics for A/B testing.
    """

    def calculate_batch_metrics(batch: list[dict[str, Any]]) -> dict[str, Any]:
        quality_scores = []
        color_diversity_scores = []
        animation_coverage_scores = []
        component_variety_scores = []

        for site in batch:
            quality = calculate_overall_quality_score(site)
            quality_scores.append(quality["overall_score"])
            color_diversity_scores.append(
                quality["metrics"]["color_diversity"]["score"]
            )
            animation_coverage_scores.append(
                quality["metrics"]["animation_coverage"]["score"]
            )
            component_variety_scores.append(
                quality["metrics"]["component_variety"]["score"]
            )

        return {
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 3)
            if quality_scores
            else 0.0,
            "avg_color_diversity": round(
                sum(color_diversity_scores) / len(color_diversity_scores), 3
            )
            if color_diversity_scores
            else 0.0,
            "avg_animation_coverage": round(
                sum(animation_coverage_scores) / len(animation_coverage_scores), 3
            )
            if animation_coverage_scores
            else 0.0,
            "avg_component_variety": round(
                sum(component_variety_scores) / len(component_variety_scores), 3
            )
            if component_variety_scores
            else 0.0,
            "site_count": len(batch),
        }

    metrics_a = calculate_batch_metrics(batch_a)
    metrics_b = calculate_batch_metrics(batch_b)

    # Calculate improvements
    improvements = {
        "quality_improvement": round(
            metrics_b["avg_quality_score"] - metrics_a["avg_quality_score"], 3
        ),
        "color_diversity_improvement": round(
            metrics_b["avg_color_diversity"] - metrics_a["avg_color_diversity"], 3
        ),
        "animation_coverage_improvement": round(
            metrics_b["avg_animation_coverage"] - metrics_a["avg_animation_coverage"], 3
        ),
        "component_variety_improvement": round(
            metrics_b["avg_component_variety"] - metrics_a["avg_component_variety"], 3
        ),
    }

    # Calculate inter-site similarity for each batch
    def calculate_batch_similarity(batch: list[dict[str, Any]]) -> float:
        if len(batch) < 2:
            return 0.0

        similarities = []
        for i in range(len(batch)):
            for j in range(i + 1, len(batch)):
                sim = calculate_visual_similarity_score(batch[i], batch[j])
                similarities.append(sim)

        return round(sum(similarities) / len(similarities), 3) if similarities else 0.0

    similarity_a = calculate_batch_similarity(batch_a)
    similarity_b = calculate_batch_similarity(batch_b)

    return {
        "batch_a": metrics_a,
        "batch_b": metrics_b,
        "improvements": improvements,
        "similarity": {
            "batch_a_avg_similarity": similarity_a,
            "batch_b_avg_similarity": similarity_b,
            "similarity_reduction": round(similarity_a - similarity_b, 3),
            "batch_b_more_unique": similarity_b < similarity_a,
        },
        "winner": "Batch B"
        if metrics_b["avg_quality_score"] > metrics_a["avg_quality_score"]
        else "Batch A",
    }


def generate_quality_report(site: dict[str, Any]) -> str:
    """Generate a human-readable quality report for a site."""

    quality = calculate_overall_quality_score(site)

    report = f"""
# Site Quality Report

**Overall Score:** {quality["overall_score"]} ({quality["grade"]})
**Status:** {"✅ Passes quality threshold" if quality["passes_quality_threshold"] else "❌ Below quality threshold"}

## Metrics Breakdown

### Color Diversity: {quality["metrics"]["color_diversity"]["score"]}
- Unique colors: {quality["metrics"]["color_diversity"]["unique_color_count"]}
- Has mesh gradient: {quality["metrics"]["color_diversity"]["has_mesh_gradient"]}
- Has advanced colors: {quality["metrics"]["color_diversity"]["has_advanced_colors"]}
- Status: {"✅ Passes" if quality["metrics"]["color_diversity"]["passes_diversity_threshold"] else "❌ Needs improvement"}

### Animation Coverage: {quality["metrics"]["animation_coverage"]["score"]}
- Animated sections: {quality["metrics"]["animation_coverage"]["animated_sections"]} / {quality["metrics"]["animation_coverage"]["total_sections"]}
- Coverage: {quality["metrics"]["animation_coverage"]["coverage"] * 100:.1f}%
- Status: {"✅ Passes" if quality["metrics"]["animation_coverage"]["passes_threshold"] else "❌ Needs improvement"}

### Component Variety: {quality["metrics"]["component_variety"]["score"]}
- Unique components: {quality["metrics"]["component_variety"]["unique_components"]}
- Total sections: {quality["metrics"]["component_variety"]["total_sections"]}
- Status: {"✅ Passes" if quality["metrics"]["component_variety"]["passes_threshold"] else "❌ Needs improvement"}

## Recommendations

"""

    # Add specific recommendations
    if not quality["metrics"]["color_diversity"]["passes_diversity_threshold"]:
        report += "- **Color Diversity:** Expand color palette to 8-12 colors. Use complementary and analogous colors.\n"

    if not quality["metrics"]["animation_coverage"]["passes_threshold"]:
        report += "- **Animation Coverage:** Add scroll-triggered animations to more sections. Target 80%+ coverage.\n"

    if not quality["metrics"]["component_variety"]["passes_threshold"]:
        report += "- **Component Variety:** Diversify component types. Avoid reusing the same component pattern.\n"

    if quality["passes_quality_threshold"]:
        report += "- ✅ Site meets all quality thresholds. Great work!\n"

    return report
