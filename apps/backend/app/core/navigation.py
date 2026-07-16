"""
Navigation menu generation system - creates smart navigation menus based on sections and industry.
Part of Phase 4: Components & Animation implementation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_navigation(
    sections: list[dict[str, Any]],
    industry: str,
    logo_url: str | None = None,
    company_name: str = "",
    theme: str = "light",
) -> dict[str, Any]:
    """
    Generate navigation menu based on sections and industry.

    Args:
        sections: List of section dictionaries with 'kind' field
        industry: Detected industry
        logo_url: Optional logo URL
        company_name: Company name for text fallback
        theme: "light" or "dark"

    Returns:
        Navigation configuration dictionary
    """

    # Core nav items (always present)
    nav_items: list[dict[str, Any]] = [
        {"label": "Home", "href": "#home", "is_cta": False},
    ]

    # Section-based nav mapping
    section_map: dict[str, dict[str, str]] = {
        "services": {"label": "Services", "href": "#services"},
        "about": {"label": "About", "href": "#about"},
        "proof": {"label": "Work", "href": "#work"},
        "testimonials": {"label": "Testimonials", "href": "#testimonials"},
        "process": {"label": "Process", "href": "#process"},
        "pricing": {"label": "Pricing", "href": "#pricing"},
        "team": {"label": "Team", "href": "#team"},
        "portfolio": {"label": "Portfolio", "href": "#portfolio"},
        "case_studies": {"label": "Case Studies", "href": "#case-studies"},
        "blog": {"label": "Blog", "href": "#blog"},
        "contact": {"label": "Contact", "href": "#contact"},
    }

    # Add section-based navigation items
    for section in sections:
        kind = section.get("kind", "")
        if kind in section_map:
            nav_item: dict[str, Any] = section_map[kind].copy()
            nav_item["is_cta"] = False

            # Avoid duplicates
            if not any(item["href"] == nav_item["href"] for item in nav_items):
                nav_items.append(nav_item)

    # Industry-specific adjustments
    nav_items = _apply_industry_adjustments(nav_items, industry, sections)

    # Add CTA button (always last)
    cta_label, cta_href = _get_industry_cta(industry)
    nav_items.append(
        {
            "label": cta_label,
            "href": cta_href,
            "is_cta": True,
        }
    )

    # Detect navigation style based on industry
    nav_style = _detect_nav_style(industry)

    return {
        "style": nav_style,
        "items": nav_items,
        "logo": {
            "url": logo_url,
            "alt": company_name,
            "text_fallback": company_name,
        },
        "theme": theme,
        "sticky": True,
        "animation": "fade_in_on_scroll",
    }


def _apply_industry_adjustments(
    nav_items: list[dict[str, Any]],
    industry: str,
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Apply industry-specific adjustments to navigation items.
    """

    # Creative Agency: Rename "Work" to "Portfolio"
    if industry == "creative_agency":
        for item in nav_items:
            if item["label"] == "Work":
                item["label"] = "Portfolio"

    # E-commerce: Add "Shop" link
    if industry == "ecommerce_fashion":
        if not any(item["label"] == "Shop" for item in nav_items):
            nav_items.insert(1, {"label": "Shop", "href": "#products", "is_cta": False})

    # SaaS: Add "Features" if services section exists
    if industry == "saas":
        if any(s.get("kind") == "services" for s in sections):
            for item in nav_items:
                if item["label"] == "Services":
                    item["label"] = "Features"

    # Legal/Finance: Add "Practice Areas" if services section exists
    if industry == "legal_finance":
        if any(s.get("kind") == "services" for s in sections):
            for item in nav_items:
                if item["label"] == "Services":
                    item["label"] = "Practice Areas"

    # Real Estate: Add "Properties" if applicable
    if industry == "real_estate":
        if not any(item["label"] == "Properties" for item in nav_items):
            nav_items.insert(
                1, {"label": "Properties", "href": "#properties", "is_cta": False}
            )

    # Health/Wellness: Rename "Services" to "Care"
    if industry == "health_wellness":
        for item in nav_items:
            if item["label"] == "Services":
                item["label"] = "Care"

    return nav_items


def _get_industry_cta(industry: str) -> tuple[str, str]:
    """
    Get industry-specific CTA text and href.

    Returns:
        Tuple of (label, href)
    """
    cta_map = {
        "creative_agency": ("Start a Project", "#contact"),
        "saas": ("Get Started", "#signup"),
        "legal_finance": ("Schedule Consultation", "#contact"),
        "consulting": ("Book a Call", "#contact"),
        "ecommerce_fashion": ("Shop Now", "#shop"),
        "tech": ("Try for Free", "#signup"),
        "real_estate": ("View Properties", "#properties"),
        "health_wellness": ("Book Appointment", "#booking"),
        "education": ("Enroll Now", "#enroll"),
        "hospitality": ("Book Now", "#booking"),
    }

    return cta_map.get(industry, ("Get Started", "#contact"))


def _detect_nav_style(industry: str) -> str:
    """
    Detect navigation style based on industry.

    Returns:
        Navigation style: "minimal", "full_screen", "sidebar", "sticky_top", "center_aligned"
    """
    style_map = {
        "creative_agency": "full_screen",  # Burger menu → full-screen overlay
        "saas": "sticky_top",  # Always visible, clean
        "legal_finance": "minimal",  # Top bar, text links
        "consulting": "minimal",
        "ecommerce_fashion": "center_aligned",  # Logo center, links flanking
        "tech": "sticky_top",
        "real_estate": "minimal",
        "health_wellness": "sticky_top",
        "education": "sticky_top",
        "hospitality": "center_aligned",
    }

    return style_map.get(industry, "sticky_top")


def generate_mobile_nav(nav_config: dict[str, Any]) -> dict[str, Any]:
    """
    Generate mobile-specific navigation configuration.

    Args:
        nav_config: Desktop navigation configuration

    Returns:
        Mobile navigation configuration
    """
    return {
        "style": "hamburger",  # Mobile always uses hamburger menu
        "items": nav_config["items"],
        "logo": nav_config["logo"],
        "theme": nav_config["theme"],
        "animation": "slide_in",
        "overlay": True,
        "full_screen": True,
    }


def add_scroll_behavior(nav_config: dict[str, Any]) -> dict[str, Any]:
    """
    Add scroll-triggered navigation behavior.

    Args:
        nav_config: Navigation configuration

    Returns:
        Enhanced navigation configuration with scroll behavior
    """
    nav_config["scroll_behavior"] = {
        "hide_on_scroll_down": False,  # Keep visible
        "shrink_on_scroll": True,  # Reduce height after scrolling
        "background_opacity_change": True,  # Increase opacity on scroll
        "initial_opacity": 0.0,  # Transparent at top
        "scrolled_opacity": 1.0,  # Solid after scrolling
        "shrink_threshold": 100,  # Pixels scrolled before shrinking
    }

    return nav_config
