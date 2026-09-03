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
    proof_markers = re.compile(
        r"testimonial|review|rating|customer quote|what clients say", re.I
    )
    if proof_markers.search(html):
        quotes = [quote.lower() for quote in (approved_proof or []) if quote]
        if not quotes or not any(quote in html.lower() for quote in quotes):
            result.issues.append(
                SemanticIssue(
                    "proof.evidence_required",
                    "Proof content has no approved evidence",
                    "[class*=testimonial], [id*=review]",
                )
            )
    return result


def sanitize_unsupported_proof(
    html: str, *, approved_proof: list[str] | None = None
) -> str:
    """Remove entire unsupported proof sections and their navigation links."""
    if approved_proof:
        return html
    section_pattern = re.compile(
        r"<(?P<tag>section|article|aside|div)\b(?=[^>]*(?:id|class)\s*=\s*['\"][^'\"]*(?:testimonial|review|rating|social-proof)[^'\"]*['\"])[^>]*>.*?</(?P=tag)\s*>",
        re.I | re.S,
    )
    cleaned = section_pattern.sub("", html)
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
