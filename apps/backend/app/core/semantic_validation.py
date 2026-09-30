"""Semantic gates for generated HTML components."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticIssue:
    rule_id: str
    message: str
    selector: str | None = None
    context: str | None = None


@dataclass
class SemanticValidation:
    issues: list[SemanticIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.issues


def validate_semantics(
    html: str,
    *,
    require_footer: bool = False,
    require_media: bool = False,
    approved_images: set[str] | None = None,
    approved_proof: list[str] | None = None,
    approved_evidence_ids: set[str] | None = None,
    hero_mode: str | None = None,
    require_hero_media: bool = False,
) -> SemanticValidation:
    result = SemanticValidation()
    footer_matches = list(
        re.finditer(r"<footer\b[^>]*>(.*?)</footer\s*>", html, re.I | re.S)
    )
    if require_footer and len(footer_matches) != 1:
        result.issues.append(
            SemanticIssue(
                "footer.required", "Exactly one footer landmark is required", "footer"
            )
        )
    if footer_matches and re.search(
        r"<main\b[^>]*>(?:(?!</main\s*>).)*<footer\b", html, re.I | re.S
    ):
        result.issues.append(
            SemanticIssue(
                "footer.outside_main", "Footer must be outside main", "main footer"
            )
        )
    if require_media:
        images = re.findall(r"<img\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", html, re.I)
        if not images:
            result.issues.append(
                SemanticIssue("hero.media_required", "Required media is missing", "img")
            )
        elif approved_images and not any(image in approved_images for image in images):
            result.issues.append(
                SemanticIssue("hero.asset_approved", "No approved image is used", "img")
            )
    if require_hero_media:
        approved = approved_images or set()
        hero_match = re.search(
            r"<(?:header|section)\b[^>]*(?:id|class)\s*=\s*['\"][^'\"]*\bhero\b[^'\"]*['\"][^>]*>(.*?)</(?:header|section)\s*>",
            html,
            re.I | re.S,
        ) or re.search(r"<header\b[^>]*>(.*?)</header\s*>", html, re.I | re.S)
        hero_html = hero_match.group(1) if hero_match else ""
        hero_images = list(re.finditer(r"<img\b[^>]*>", hero_html, re.I | re.S))
        hero_approved = [
            image
            for image in hero_images
            if re.search(
                rf"\bsrc\s*=\s*['\"](?:{'|'.join(re.escape(url) for url in sorted(approved))})['\"]",
                image.group(0),
                re.I,
            )
        ]
        if not hero_approved:
            result.issues.append(
                SemanticIssue(
                    "hero.asset_required",
                    "Image-led heroes must use an approved image in the hero",
                    "header img, [id*=hero] img, [class*=hero] img",
                )
            )
        else:
            tag = hero_approved[0].group(0)
            if not re.search(r"\bdata-hero-media(?:\s*=\s*['\"][^'\"]*['\"])?|\bclass\s*=\s*['\"][^'\"]*(?:hero-media|hero-visual|hero)[^'\"]*['\"]", tag, re.I):
                result.issues.append(
                    SemanticIssue(
                        "hero.asset_role",
                        "Hero media must declare a meaningful visual role",
                        "[data-hero-media], .hero-media, .hero-visual",
                    )
                )
            if not re.search(r"\b(?:width|height)\s*=\s*['\"]\d+", tag, re.I):
                result.issues.append(
                    SemanticIssue(
                        "hero.asset_dimensions",
                        "Hero media must declare intrinsic dimensions",
                        "hero img[width][height]",
                    )
                )
            if re.search(r"\bloading\s*=\s*['\"]lazy['\"]", tag, re.I):
                result.issues.append(
                    SemanticIssue(
                        "hero.asset_loading",
                        "Hero media must load eagerly",
                        "hero img[loading=eager]",
                    )
                )
    if hero_mode == "typography_only" and re.search(
        r"<(?:img|video|canvas)\b|data-media-required|class\s*=\s*['\"][^'\"]*(?:hero-media|image-shell|media-placeholder)[^'\"]*['\"]",
        html,
        re.I,
    ):
        result.issues.append(SemanticIssue("hero.typography_only_no_media_shell", "Typography-only hero must not contain a fake media shell", "[data-media-required], .hero-media"))
    proof_markers = re.compile(r"testimonial|review|rating|customer quote|what clients say|award|badge|\b(?:[0-9]+(?:\.[0-9]+)?\s*(?:stars?|reviews?|projects?|years?))\b|client(?:\s+name)?|project\s+location", re.I)
    if proof_markers.search(html):
        quotes = [quote.lower() for quote in (approved_proof or []) if quote]
        evidence_ids = approved_evidence_ids or set()
        ids_in_markup = set(re.findall(r"data-evidence-id\s*=\s*['\"]([^'\"]+)['\"]", html, re.I))
        if not evidence_ids or not ids_in_markup.intersection(evidence_ids) or (quotes and not any(quote in html.lower() for quote in quotes)):
            result.issues.append(
                SemanticIssue(
                    "proof.evidence_required",
                    "Proof content requires an exact approved evidence ID",
                    "[class*=testimonial], [id*=review]",
                )
            )
        # Validate each proof-bearing card independently. A valid quote and ID
        # elsewhere on the page must not authorize an invented neighboring
        # testimonial, rating, badge, or author.
        proof_container_pattern = re.compile(
            r"<(?P<tag>section|article|blockquote|aside|div)\b(?=[^>]*(?:id|class)\s*=\s*['\"][^'\"]*(?:testimonial|review|quote|proof|rating|award|badge|metric)[^'\"]*['\"])[^>]*>(?P<body>.*?)</(?P=tag)\s*>",
            re.I | re.S,
        )
        for match in proof_container_pattern.finditer(html):
            block = match.group(0)
            block_ids = set(re.findall(r"data-evidence-id\s*=\s*['\"]([^'\"]+)['\"]", block, re.I))
            if len(block_ids) != 1 or not block_ids.issubset(evidence_ids):
                result.issues.append(
                    SemanticIssue(
                        "proof.card_evidence_required",
                        "Every proof card requires exactly one approved evidence ID",
                        "[data-evidence-id]",
                    )
                )
                break
            if quotes and not any(quote in block.lower() for quote in quotes):
                result.issues.append(
                    SemanticIssue(
                        "proof.card_quote_required",
                        "Every proof card requires its own approved quote",
                        "[class*=testimonial], [id*=review]",
                    )
                )
                break
    return result


def sanitize_unsupported_proof(
    html: str, *, approved_proof: list[str] | None = None
) -> str:
    """Remove entire unsupported proof sections and their navigation links."""
    if approved_proof:
        return html
    section_pattern = re.compile(
        r"<(?P<tag>section|article|aside|div)\b(?=[^>]*(?:id|class)\s*=\s*['\"][^'\"]*(?:testimonial|review|rating|social-proof|award|badge|metrics?)[^'\"]*['\"])[^>]*>.*?</(?P=tag)\s*>",
        re.I | re.S,
    )
    cleaned = section_pattern.sub("", html)
    # Models sometimes wrap proof copy in a neutral container. Remove those
    # sections too when no approved evidence exists, before semantic validation.
    content_pattern = re.compile(
        r"<(?P<tag>section|article|aside|div)\b[^>]*>"
        r"(?:(?!</?\1\b).)*?"
        r"(?:testimonial|review|rating|customer quote|what clients say|"
        r"\b\d+(?:\.\d+)?\s*(?:stars?|reviews?)|award)"
        r".*?</(?P=tag)\s*>",
        re.I | re.S,
    )
    cleaned = content_pattern.sub("", cleaned)
    cleaned = re.sub(
        r"\s*<a\b[^>]*(?:href|aria-controls)\s*=\s*['\"][^'\"]*(?:testimonial|review|rating)[^'\"]*['\"][^>]*>.*?</a\s*>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"<style\b[^>]*>.*?(?:testimonial|review|rating).*?</style\s*>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    return re.sub(
        r"<script\b[^>]*>.*?(?:testimonial|review|rating).*?</script\s*>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
