"""Deterministic content and brand contracts for generated site artifacts."""

from __future__ import annotations

import html as html_module
import hashlib
import re
from html.parser import HTMLParser
from typing import Any


_PROOF_KEYS = {"testimonial", "testimonials", "review", "reviews", "socialProof", "proof"}
_PROOF_PURPOSES = {"testimonial", "testimonials", "review", "reviews", "socialproof", "social-proof", "proof"}


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _is_plausible_contact_value(key: str, value: Any) -> bool:
    """Reject obviously misclassified schedule text without inventing a correction."""
    if not value:
        return False
    if key.casefold() not in {"hours", "officehours", "openinghours"}:
        return True
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) > 80:
        return False
    return bool(
        re.search(
            r"\b(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?|open|closed|daily|weekdays|weekends|by appointment|business hours|24\s*/\s*7)\b|\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?\b",
            text,
            re.I,
        )
    )


def _norm(value: Any) -> str:
    text = html_module.unescape(str(value or "")).replace("\u2014", "-").replace("\u2013", "-")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _source_text(source: str) -> str:
    return _norm(source)


class _VisibleHTMLParser(HTMLParser):
    """Collect visible text and section semantics without script/attribute noise."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.text: list[str] = []
        self.sections: list[dict[str, str]] = []
        self._section_stack: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "template", "noscript"}:
            self.skip_depth += 1
            return
        if tag == "section":
            values = {key.lower(): value or "" for key, value in attrs}
            record: dict[str, Any] = {
                "attributes": " ".join(values.values()),
                "text": [],
            }
            self.sections.append(record)
            self._section_stack.append(record)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "template", "noscript"}:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag == "section" and self._section_stack:
            self._section_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.text.append(data)
        for section in self._section_stack:
            section["text"].append(data)


def _contract_text(source: str, *, rendered_html: bool) -> str:
    if not rendered_html:
        # Remove comments and JSX/HTML tags so attributes, imports, and prose in
        # comments cannot satisfy a copy contract. Literal text split by tags is
        # retained with whitespace between adjacent nodes.
        cleaned = re.sub(r"/\*.*?\*/|//[^\n]*|\{\s*/\*.*?\*/\s*\}", " ", source, flags=re.S)
        cleaned = re.sub(r"^\s*import\b[^\n]*", " ", cleaned, flags=re.M)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        return _norm(cleaned)
    parser = _VisibleHTMLParser()
    parser.feed(source)
    parser.close()
    return _norm(" ".join(parser.text))


def _has_semantic_phrase(actual: str, expected: str) -> bool:
    """Match copy across element boundaries without accepting unrelated words."""
    expected_tokens = re.findall(r"[\w]+", _norm(expected))
    actual_tokens = re.findall(r"[\w]+", actual)
    if not expected_tokens:
        return True
    expected_joined = " ".join(expected_tokens)
    actual_joined = " ".join(actual_tokens)
    if expected_joined in actual_joined:
        return True
    # Permit small punctuation/markup gaps while keeping the phrase ordered.
    cursor = 0
    for token in expected_tokens:
        try:
            cursor = actual_tokens.index(token, cursor) + 1
        except ValueError:
            return False
    return True


def _color_is_present(expected: str, css: str, role: str) -> bool:
    candidate = _norm(expected)
    if not candidate:
        return True
    haystack = css.casefold()
    if candidate in haystack:
        return True
    # CSS custom properties and derived rgb/rgba representations are valid
    # renderings of the same approved color.
    role_pattern = re.compile(rf"--[\w-]*{role}[\w-]*\s*:\s*([^;}}]+)", re.I)
    if role_pattern.search(css):
        value = _norm(role_pattern.search(css).group(1))  # type: ignore[union-attr]
        if candidate in value or value in haystack:
            return True
    hex_match = re.fullmatch(r"#([0-9a-f]{3,8})", candidate, re.I)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in {3, 4}:
            digits = "".join(char * 2 for char in digits)
        rgb = tuple(int(digits[index : index + 2], 16) for index in (0, 2, 4))
        for match in re.finditer(r"rgba?\(\s*([^)]+)\)", css, re.I):
            numbers = [int(float(item)) for item in re.findall(r"\d+(?:\.\d+)?", match.group(1))[:3]]
            if len(numbers) == 3 and tuple(numbers) == rgb:
                return True
    return False


def _section_contract_errors(source: str, brief: Any, *, rendered_html: bool) -> list[str]:
    sections = _value(brief, "sections", []) or []
    if not sections or not rendered_html:
        return []
    parser = _VisibleHTMLParser()
    parser.feed(source)
    parser.close()
    errors: list[str] = []
    approved_services: list[str] = []
    extracted_content = _value(brief, "extractedContent", {}) or {}
    if isinstance(extracted_content, dict):
        approved_services.extend(str(item) for item in extracted_content.get("services", []) if item)
    if not approved_services:
        # The extraction object is intentionally not passed here; brief
        # services are the approved contract for generated output.
        approved_services = [
            str(_value(section, "headline", ""))
            for section in sections
            if _norm(_value(section, "purpose", "")) in {"services", "features"}
            and _value(section, "headline", "")
        ]
    for section in sections:
        purpose = _norm(_value(section, "purpose", ""))
        if not purpose or purpose == "section":
            continue
        if purpose in _PROOF_PURPOSES:
            # Proof sections are optional when no approved evidence exists.
            continue
        aliases = {
            "services": ("services", "service", "offerings"),
            "testimonials": ("testimonial", "review", "proof"),
            "social-proof": ("social", "proof", "testimonial", "review"),
            "cta": ("cta", "contact", "call", "next step"),
        }.get(purpose, tuple(purpose.split()))
        represented = any(
            any(alias in _norm(f"{item['attributes']} {' '.join(item['text'])}") for alias in aliases)
            for item in parser.sections
        )
        if not represented:
            errors.append(f"Approved section purpose '{purpose}' is not represented semantically")
        if purpose == "services" and approved_services:
            service_section_text = " ".join(
                " ".join(item["text"])
                for item in parser.sections
                if any(alias in _norm(item["attributes"]) for alias in ("service", "offering"))
            )
            if service_section_text:
                for service in approved_services:
                    if not _has_semantic_phrase(_norm(service_section_text), _norm(service)):
                        errors.append(f"Approved service '{service}' is not represented in the services section")
    return errors


def _cta_contract_errors(source: str, brief: Any, *, rendered_html: bool) -> list[str]:
    action = _norm(_value(brief, "conversionAction", ""))
    if not action:
        return []
    if rendered_html:
        controls = re.findall(r"<(?:a|button|form)\b[^>]*>.*?</(?:a|button|form)\s*>", source, re.I | re.S)
        controls_text = _norm(" ".join(controls))
    else:
        controls_text = _contract_text(source, rendered_html=False)
        if not re.search(r"\b(?:button|onClick|href|type\s*=\s*['\"]submit)", source, re.I):
            return ["Generated output has no actionable CTA control"]
    if not _has_semantic_phrase(controls_text, action):
        action_tokens = re.findall(r"[\w]+", action)
        if not action_tokens or not any(token in controls_text for token in action_tokens[:2]):
            return ["Primary conversion action is not represented in a CTA control"]
    return []


def _content_values(brief: Any, extraction: Any) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for label, field in (("headline", "headline"), ("subheadline", "subheadline"), ("conversion action", "conversionAction")):
        value = _value(brief, field)
        if value:
            values.append((label, str(value)))

    proof_allowed = _approved_proof_available(brief, extraction)
    for index, section in enumerate(_value(brief, "sections", []) or [], start=1):
        purpose = _norm(_value(section, "purpose", "")).replace(" ", "-")
        if purpose in _PROOF_PURPOSES and not proof_allowed:
            continue
        for label, field in ((f"section {index} headline", "headline"), (f"section {index} purpose", "purpose")):
            value = _value(section, field)
            if value:
                values.append((label, str(value)))
        for point in _value(section, "contentPoints", []) or []:
            if point:
                values.append((f"section {index} content point", str(point)))

    analysis = _value(extraction, "analysis")
    for service in (_value(analysis, "services", []) or []):
        if service:
            values.append(("approved service", str(service)))
    summary = _value(extraction, "summary")
    for service in (_value(summary, "serviceClues", []) or []):
        if service:
            values.append(("extracted service", str(service)))

    extracted_content = _value(brief, "extractedContent", {}) or {}
    if isinstance(extracted_content, dict):
        for key, items in extracted_content.items():
            if key in _PROOF_KEYS:
                continue
            for item in items or []:
                if item:
                    values.append((f"approved {key} content", str(item)))

    contacts: dict[str, Any] = {}
    brief_contacts = _value(brief, "contactInfo", {}) or {}
    if isinstance(brief_contacts, dict):
        contacts.update(brief_contacts)
    extracted_contacts = _value(extraction, "contactInfo")
    for key in ("officePhone", "emergencyPhone", "email", "address", "hours", "contactUrl"):
        value = _value(extracted_contacts, key)
        if value:
            contacts.setdefault(key, value)
    for key, value in contacts.items():
        if key not in {"sourceUrl", "confidence"} and _is_plausible_contact_value(
            key, value
        ):
            values.append((f"verified contact {key}", str(value)))
    return values


def _approved_quotes(brief: Any, extraction: Any) -> list[str]:
    quotes: list[str] = []
    extracted = _value(brief, "extractedContent", {}) or {}
    for item in (extracted.get("testimonials", []) if isinstance(extracted, dict) else []) or []:
        if isinstance(item, str) and item.strip():
            quotes.append(item.strip())
    analysis = _value(extraction, "analysis")
    for item in (_value(analysis, "testimonials", []) or []):
        quote = _value(item, "quote")
        if quote and str(quote).strip():
            quotes.append(str(quote).strip())
    for item in (_value(extraction, "extractedTestimonials", []) or []):
        quote = _value(item, "quote")
        if quote and str(quote).strip():
            quotes.append(str(quote).strip())
    return list(dict.fromkeys(quotes))


def _approved_proof_available(brief: Any, extraction: Any) -> bool:
    """Only require proof-section copy when quote evidence can be verified."""
    quotes = _approved_quotes(brief, extraction)
    if not quotes:
        return False
    analysis = _value(extraction, "analysis")
    items = list(_value(analysis, "testimonials", []) or [])
    items.extend(_value(extraction, "extractedTestimonials", []) or [])
    return any(_value(item, "id") or _value(item, "quote") for item in items)


def _proof_contract_errors(source: str, brief: Any, extraction: Any) -> list[str]:
    # Ordinary approved copy can describe an award without being a testimonial
    # or proof card. Structural award/badge markup is still checked below.
    markers = re.compile(r"testimonial|review|rating|social[- ]proof|customer quote|what clients say", re.I)
    visible = _contract_text(source, rendered_html=True)
    structural_values: list[str] = []
    for tag in re.findall(r"<[^>]+>", source):
        structural_values.extend(
            re.findall(
                r"\b(?:id|class|data-purpose|role|aria-label)\s*=\s*['\"]([^'\"]*)['\"]",
                tag,
                re.I,
            )
        )
    structural_source = " ".join(structural_values)
    if not markers.search(visible) and not re.search(
        r"(?:testimonial|review|proof|rating|award|badge)", structural_source, re.I
    ):
        return []
    quotes = [quote.casefold() for quote in _approved_quotes(brief, extraction)]
    if not quotes:
        return ["Generated proof content has no approved testimonial evidence"]
    errors: list[str] = []
    container_pattern = re.compile(
        r"<(?P<tag>section|article|blockquote|aside|div)\b(?=[^>]*(?:(?:id|class|data-purpose)\s*=\s*['\"][^'\"]*(?:testimonial|review|quote|proof|rating|award|badge)[^'\"]*['\"]|data-purpose\s*=\s*['\"]social-proof['\"]))[^>]*>(?P<body>.*?)</(?P=tag)\s*>",
        re.I | re.S,
    )
    approved_ids = set()
    testimonial_items = list(_value(_value(extraction, "analysis"), "testimonials", []) or [])
    testimonial_items.extend(_value(extraction, "extractedTestimonials", []) or [])
    for item in testimonial_items:
        value = _value(item, "id")
        if value:
            approved_ids.add(str(value).strip())
        else:
            quote = _value(item, "quote")
            if quote:
                approved_ids.add("testimonial-" + hashlib.sha1(str(quote).strip().encode("utf-8")).hexdigest()[:12])
    blocks = container_pattern.findall(source)
    if not blocks:
        return ["Generated proof content requires a semantic proof card"]
    for block in blocks:
        tag, body = block
        full_block = f"<{tag}>{body}</{tag}>"
        evidence = re.findall(r"data-evidence-id\s*=\s*['\"]([^'\"]+)['\"]", full_block, re.I)
        if len(evidence) != 1 or not approved_ids or evidence[0] not in approved_ids:
            errors.append("Every proof card requires exactly one approved evidence ID")
            break
        if not any(_has_semantic_phrase(_contract_text(full_block, rendered_html=True), quote) for quote in quotes):
            errors.append("Every proof card requires its own approved testimonial quote")
            break
    return errors


def generated_content_contract_errors(
    source: str,
    brief: Any,
    extraction: Any,
    *,
    rendered_html: bool = False,
    enforce_section_stack: bool = False,
    css: str = "",
) -> list[str]:
    """Return publication-blocking omissions from HTML or generated TSX/JS."""
    haystack = _contract_text(source, rendered_html=rendered_html)
    errors: list[str] = []
    for label, value in _content_values(brief, extraction):
        expected = _norm(value)
        if expected and not _has_semantic_phrase(haystack, expected):
            errors.append(f"Approved {label} is missing")

    if rendered_html or enforce_section_stack:
        section_count = len(re.findall(r"<section\b", source, re.I))
        all_sections = _value(brief, "sections", []) or []
        required_sections = [
            section
            for section in all_sections
            if _norm(_value(section, "purpose", "")).replace(" ", "-") not in _PROOF_PURPOSES
        ]
        required_count = max(3, len(required_sections))
        if section_count < required_count:
            errors.append(f"Generated HTML requires at least {required_count} content sections; found {section_count}")
    errors.extend(_section_contract_errors(source, brief, rendered_html=rendered_html))
    errors.extend(_cta_contract_errors(source, brief, rendered_html=rendered_html))

    assets = _value(brief, "brandAssets")
    palette_source = _norm(css or source)
    for label, color in (("primary", _value(assets, "primaryColor")), ("secondary", _value(assets, "secondaryColor"))):
        expected = _norm(color)
        if expected and not _color_is_present(str(color), palette_source, label):
            errors.append(f"Approved {label} brand color is missing from generated CSS")
    errors.extend(_proof_contract_errors(source, brief, extraction))
    return errors
