from __future__ import annotations

import asyncio
import hashlib
import importlib
import logging
import os
import re
import ssl
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from app.core import asset_metadata
from app.core.asset_downloader import AssetDownloader
from app.core.config import get_settings

USER_AGENT = "LenQuantBot/0.3 (+internal extraction)"
FETCH_TIMEOUT = 12

settings = get_settings()
logger = logging.getLogger(__name__)


def _max_pages() -> int:
    return int(get_settings().crawl_max_pages or 6)


def _origin_key(raw_url: str) -> tuple[str, int | None]:
    parsed = urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname, parsed.port


def _same_origin(base_url: str, candidate_url: str) -> bool:
    return bool(candidate_url) and _origin_key(base_url) == _origin_key(candidate_url)


def normalize_site_url(raw_url: str) -> tuple[str, str]:
    cleaned = raw_url.strip()
    if not cleaned:
        raise ValueError("website_url_required")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    if not parsed.netloc:
        raise ValueError("website_url_invalid")
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if not hostname:
        raise ValueError("website_url_invalid")
    if hostname.startswith("www."):
        hostname = hostname[4:]

    normalized = parsed._replace(
        scheme=parsed.scheme.lower() or "https",
        netloc=hostname + (f":{parsed.port}" if parsed.port else ""),
        path=parsed.path.rstrip("/") or "",
        params="",
        query="",
        fragment="",
    )
    normalized_url = urlunparse(normalized)
    if normalized_url.endswith("/"):
        normalized_url = normalized_url[:-1]
    return normalized_url, hostname


@dataclass
class PageSignals:
    title: str | None = None
    meta_description: str | None = None
    canonical_url: str | None = None
    theme_color: str | None = None
    font_family: str | None = None
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    ctas: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)
    logo_candidates: list[str] = field(default_factory=list)
    body_text: list[str] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _SectionState:
    tag_name: str
    attrs: dict[str, str]
    selector: str | None
    text: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    ctas: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)


class _SignalParser(HTMLParser):
    SECTION_TAGS = {"header", "main", "section", "article", "aside", "footer"}
    TEXT_TAGS = {
        "title",
        "h1",
        "h2",
        "h3",
        "p",
        "li",
        "button",
        "a",
        "strong",
        "em",
        "span",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.signals = PageSignals()
        self._current_tag: str | None = None
        self._text_buffer: list[str] = []
        self._text_target: str | None = None
        self._in_style = False
        self._style_chunks: list[str] = []
        self._section_stack: list[_SectionState] = []
        self._section_index = 0

    def _selector(self, tag: str, attrs: dict[str, str | None]) -> str | None:
        ident = (attrs.get("id") or "").strip()
        classes = (attrs.get("class") or "").strip().split()
        if ident:
            return f"{tag}#{ident}"
        if classes:
            return f"{tag}." + ".".join(classes[:3])
        return tag

    def _asset(self, kind: str, url: str, label: str | None, source: str) -> None:
        value = (url or "").strip()
        if not value or value.startswith("data:"):
            return
        asset = {"kind": kind, "url": value, "label": label, "source": source}
        if asset not in self.signals.assets:
            self.signals.assets.append(asset)
        if self._section_stack:
            self._section_stack[-1].assets.append(value)

    def _section_type(self, state: _SectionState) -> str:
        hint = " ".join(
            filter(
                None,
                [
                    state.tag_name,
                    state.attrs.get("id"),
                    state.attrs.get("class"),
                    " ".join(state.headings[:2]),
                    " ".join(state.ctas[:2]),
                ],
            )
        ).lower()
        if state.tag_name == "header" or any(
            w in hint for w in ["hero", "masthead", "banner"]
        ):
            return "hero" if state.tag_name != "header" or state.headings else "header"
        if state.tag_name == "footer":
            return "footer"
        rules = [
            (
                "services",
                ["service", "offering", "solution", "treatment", "practice area"],
            ),
            (
                "proof",
                [
                    "testimonial",
                    "review",
                    "case",
                    "client",
                    "result",
                    "trusted",
                    "award",
                ],
            ),
            ("about", ["about", "story", "mission", "team", "who we are"]),
            ("process", ["process", "how it works", "method", "approach", "steps"]),
            ("pricing", ["pricing", "plans", "packages", "rates"]),
            ("gallery", ["gallery", "portfolio", "work", "projects", "photos"]),
            ("contact", ["contact", "book", "schedule", "quote", "location"]),
        ]
        for section_type, terms in rules:
            if any(term in hint for term in terms):
                return section_type
        return "unknown"

    def _finish_section(self, state: _SectionState) -> None:
        text = " ".join(dict.fromkeys(t.strip() for t in state.text if t.strip()))
        # Less strict filtering: allow sections with headings even if text is short
        if len(text) < 20 and not state.headings and not state.images:
            return
        notes: list[str] = []
        if not state.headings:
            notes.append("Add a clearer section headline.")
        if not state.ctas and self._section_type(state) in {
            "hero",
            "services",
            "contact",
        }:
            notes.append("Clarify the next action for this section.")
        if len(text) > 900:
            notes.append("Condense dense copy into a sharper premium narrative.")
        confidence = min(
            92,
            38
            + len(state.headings) * 14
            + len(state.ctas) * 10
            + min(len(text), 500) // 20,
        )
        self.signals.sections.append(
            {
                "id": f"section-{self._section_index}",
                "index": self._section_index,
                "type": self._section_type(state),
                "tagName": state.tag_name,
                "selector": state.selector,
                "heading": state.headings[0] if state.headings else None,
                "text": text[:1800],
                "ctas": list(dict.fromkeys(state.ctas))[:6],
                "imageUrls": list(dict.fromkeys(state.images))[:10],
                "assetUrls": list(dict.fromkeys(state.assets))[:15],
                "improvementNotes": notes,
                "confidence": confidence,
            }
        )
        self._section_index += 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs}
        self._current_tag = tag.lower()

        if self._current_tag in self.SECTION_TAGS:
            self._section_stack.append(
                _SectionState(
                    tag_name=self._current_tag,
                    attrs={k: v or "" for k, v in attr_map.items()},
                    selector=self._selector(self._current_tag, attr_map),
                )
            )

        if self._current_tag in self.TEXT_TAGS:
            self._text_target = self._current_tag
            self._text_buffer = []

        if self._current_tag == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            content = attr_map.get("content") or ""
            if (
                name in {"description", "og:description"}
                and content
                and not self.signals.meta_description
            ):
                self.signals.meta_description = content.strip()
            if (
                name in {"theme-color", "msapplication-tilecolor"}
                and content
                and not self.signals.theme_color
            ):
                self.signals.theme_color = content.strip()
            if name in {"og:image", "twitter:image"} and content:
                self.signals.images.append(content.strip())
                self._asset("image", content, name, "meta")

        if self._current_tag == "link":
            rel = (attr_map.get("rel") or "").lower()
            href = attr_map.get("href") or ""
            if rel == "canonical" and href and not self.signals.canonical_url:
                self.signals.canonical_url = href.strip()
            if rel in {"icon", "shortcut icon", "apple-touch-icon"} and href:
                self.signals.images.append(href.strip())
                self._asset("icon", href, rel, "link")
            if "stylesheet" in rel and href:
                self._asset("stylesheet", href, rel, "link")
            if "font" in rel and href:
                self.signals.font_family = href.strip()
                self._asset("font", href, rel, "link")

        if self._current_tag == "script":
            src = attr_map.get("src") or ""
            if src:
                self._asset("script", src, None, "script")

        if self._current_tag in {"img", "source", "video"}:
            src = (
                attr_map.get("src")
                or attr_map.get("srcset")
                or attr_map.get("poster")
                or ""
            )
            if src and "," in src:
                src = src.split(",", 1)[0].strip().split(" ", 1)[0]
            alt = attr_map.get("alt") or ""
            title = attr_map.get("title") or ""
            candidate = src.strip() or alt.strip() or title.strip()
            if candidate:
                self.signals.images.append(candidate)
                if self._section_stack:
                    self._section_stack[-1].images.append(candidate)
            kind = "video" if self._current_tag == "video" else "image"
            self._asset(kind, src, alt or title or None, self._current_tag)
            hint = f"{alt} {title} {src}".lower()
            if "logo" in hint:
                self.signals.logo_candidates.append(candidate or src.strip())

        if self._current_tag in {"a", "button"}:
            href = attr_map.get("href") or ""
            self.signals.links.append((href.strip(), ""))
            class_text = " ".join(
                filter(None, [attr_map.get("class"), attr_map.get("id")])
            ).lower()
            if "cta" in class_text or "btn" in class_text or "button" in class_text:
                self._text_target = "cta"
                self._text_buffer = []

        if self._current_tag == "style":
            self._in_style = True
            self._style_chunks = []

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data.strip())
        if not text:
            return
        if self._text_target:
            self._text_buffer.append(text)
        # Capture ALL visible text content (not just specific containers)
        # This ensures we get text from divs, paragraphs, spans, etc.
        if self._current_tag not in {"script", "style", "noscript", "head"}:
            self.signals.body_text.append(text)
        if self._section_stack and self._current_tag not in {
            "script",
            "style",
            "noscript",
        }:
            self._section_stack[-1].text.append(text)
        if self._in_style:
            self._style_chunks.append(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._text_target == tag or self._text_target == "cta":
            text = " ".join(self._text_buffer).strip()
            if tag == "title" and text and not self.signals.title:
                self.signals.title = text
            elif tag == "h1" and text:
                self.signals.h1.append(text)
                if self._section_stack:
                    self._section_stack[-1].headings.append(text)
            elif tag in {"h2", "h3"} and text:
                if tag == "h2":
                    self.signals.h2.append(text)
                if self._section_stack:
                    self._section_stack[-1].headings.append(text)
            elif tag in {"a", "button"} and text:
                if self.signals.links:
                    href, _ = self.signals.links[-1]
                    self.signals.links[-1] = (href, text)
                if self._text_target == "cta" or _looks_like_cta(text):
                    self.signals.ctas.append(text)
                    if self._section_stack:
                        self._section_stack[-1].ctas.append(text)
            elif text:
                self.signals.body_text.append(text)
            self._text_target = None
            self._text_buffer = []

        if tag == "style" and self._in_style:
            style_text = " ".join(self._style_chunks)
            if not self.signals.font_family:
                font_match = re.search(
                    r"font-family\s*:\s*([^;]+)", style_text, re.IGNORECASE
                )
                if font_match:
                    self.signals.font_family = font_match.group(1).strip().strip("\"'")
            self._in_style = False
            self._style_chunks = []

        if tag in self.SECTION_TAGS and self._section_stack:
            state = self._section_stack.pop()
            if state.tag_name == tag:
                self._finish_section(state)
            elif self._section_stack:
                self._section_stack.append(state)

    def close(self) -> None:
        super().close()
        while self._section_stack:
            self._finish_section(self._section_stack.pop())


def _looks_like_cta(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in [
            "contact",
            "get started",
            "book",
            "demo",
            "quote",
            "learn more",
            "consult",
            "talk",
            "call",
            "schedule",
        ]
    )


def _fetch_url(url: str) -> tuple[str, str, dict[str, str]]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    context = ssl.create_default_context()
    with urlopen(request, timeout=FETCH_TIMEOUT, context=context) as response:
        body = response.read().decode("utf-8", errors="replace")
        final_url = response.geturl()
        headers = {key.lower(): value for key, value in response.headers.items()}
        return body, final_url, headers


def _playwright_fetch(url: str) -> dict[str, Any] | None:
    """Fetch a page using Playwright to get JS-rendered content.
    Returns None if Playwright is unavailable so caller can fall back."""
    if not get_settings().extraction_enable_visual_capture:
        return None
    try:
        sync_playwright = importlib.import_module("playwright.sync_api").sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1440, "height": 900},
                user_agent=USER_AGENT,
            )
            response = page.goto(url, wait_until="networkidle", timeout=20000)
            final_url = page.url
            status = response.status if response else 0

            rendered_html = page.content()

            page_data = page.evaluate("""
            () => {
                const getStyle = (el, prop) => window.getComputedStyle(el)[prop];
                const sections = Array.from(document.querySelectorAll('header, main > section, section, article, footer'));
                return {
                    meta: Array.from(document.querySelectorAll('meta')).reduce((acc, meta) => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        if (name) acc[name] = meta.getAttribute('content');
                        return acc;
                    }, {}),
                    cleanedText: document.body ? document.body.innerText : "",
                    fonts: Array.from(new Set(Array.from(document.querySelectorAll('*')).slice(0, 500).map(el => getStyle(el, 'fontFamily')))),
                    colors: Array.from(new Set(
                        Array.from(document.querySelectorAll('*')).slice(0, 500).map(el => getStyle(el, 'backgroundColor'))
                        .concat(Array.from(document.querySelectorAll('*')).slice(0, 500).map(el => getStyle(el, 'color')))
                    )),
                    headings: Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(el => el.innerText),
                    links: Array.from(document.querySelectorAll('a[href]')).map(el => ({href: el.href, text: el.innerText.trim()})).filter(l => l.href),
                    images: Array.from(document.querySelectorAll('img[src]')).map(el => ({src: el.src, alt: el.alt || ''})),
                    sectionsData: sections.map((sec, idx) => ({
                        index: idx,
                        tagName: sec.tagName.toLowerCase(),
                        id: sec.id || '',
                        className: sec.className || '',
                        html: sec.outerHTML.slice(0, 8000),
                        text: sec.innerText.slice(0, 2000),
                        headings: Array.from(sec.querySelectorAll('h1,h2,h3,h4')).map(h => h.innerText),
                        ctas: Array.from(sec.querySelectorAll('a, button')).filter(el =>
                            /contact|get started|book|demo|quote|learn more|consult|schedule|call|talk|sign up|try|free/i.test(el.innerText)
                        ).map(el => el.innerText.trim()),
                        images: Array.from(sec.querySelectorAll('img[src]')).map(el => el.src),
                        computedStyles: {
                            backgroundColor: getStyle(sec, 'backgroundColor'),
                            color: getStyle(sec, 'color'),
                            fontFamily: getStyle(sec, 'fontFamily'),
                            padding: getStyle(sec, 'padding'),
                        }
                    }))
                };
            }
            """)

            page.close()
            browser.close()

            if status >= 400:
                return {
                    "ok": False,
                    "body": rendered_html,
                    "finalUrl": final_url,
                    "headers": {},
                    "error": f"http_{status}",
                    "pageData": page_data,
                    "renderedByPlaywright": True,
                }

            return {
                "ok": True,
                "body": rendered_html,
                "finalUrl": final_url,
                "headers": {},
                "error": None,
                "pageData": page_data,
                "renderedByPlaywright": True,
            }
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return None


def _safe_fetch(url: str) -> dict[str, Any]:
    # Try Playwright first to get JS-rendered content
    pw_result = _playwright_fetch(url)
    if pw_result is not None:
        return pw_result

    # Fallback to urllib for raw HTML
    try:
        body, final_url, headers = _fetch_url(url)
        return {
            "ok": True,
            "body": body,
            "finalUrl": final_url,
            "headers": headers,
            "error": None,
            "renderedByPlaywright": False,
        }
    except HTTPError as exc:
        return {
            "ok": False,
            "body": None,
            "finalUrl": url,
            "headers": {},
            "error": f"http_{exc.code}",
            "renderedByPlaywright": False,
        }
    except URLError as exc:
        return {
            "ok": False,
            "body": None,
            "finalUrl": url,
            "headers": {},
            "error": f"url_{getattr(exc, 'reason', 'fetch_failed')}",
            "renderedByPlaywright": False,
        }
    except Exception as exc:  # pragma: no cover - network edge cases
        return {
            "ok": False,
            "body": None,
            "finalUrl": url,
            "headers": {},
            "error": str(exc),
            "renderedByPlaywright": False,
        }


def _parse_html(body: str) -> PageSignals:
    parser = _SignalParser()
    parser.feed(body)
    parser.close()
    return parser.signals


def _parse_sitemap_urls(body: str) -> list[str]:
    urls: list[str] = []
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return urls

    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag == "loc" and element.text:
            urls.append(element.text.strip())
    return urls


def _absolute_url(page_url: str, value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or cleaned.startswith("data:"):
        return cleaned
    return urljoin(page_url, cleaned)


def _normalize_assets(
    page_url: str, assets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for asset in assets:
        url = _absolute_url(page_url, str(asset.get("url") or ""))
        if not url or url.startswith("data:"):
            continue
        kind = str(asset.get("kind") or "unknown")
        key = (kind, url)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "kind": kind,
                "url": url,
                "label": asset.get("label"),
                "source": asset.get("source"),
            }
        )
    return normalized


def _normalize_sections(
    page_url: str, sections: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    max_sections = int(get_settings().extraction_max_sections_per_page or 14)
    normalized: list[dict[str, Any]] = []
    for index, section in enumerate(sections[:max_sections]):
        images = [
            _absolute_url(page_url, value) for value in section.get("imageUrls", [])
        ]
        assets = [
            _absolute_url(page_url, value) for value in section.get("assetUrls", [])
        ]
        normalized.append(
            {
                **section,
                "id": f"section-{index}",
                "index": index,
                "imageUrls": list(dict.fromkeys(filter(None, images))),
                "assetUrls": list(dict.fromkeys(filter(None, assets))),
            }
        )
    return normalized


def _raw_html_payload(body: str) -> dict[str, Any]:
    encoded = body.encode("utf-8", errors="ignore")
    limit = int(get_settings().extraction_raw_html_max_chars or 0)
    should_store = bool(get_settings().extraction_store_raw_html)
    stored = body if should_store else None
    truncated = False
    if stored is not None and limit > 0 and len(stored) > limit:
        stored = stored[:limit]
        truncated = True
    return {
        "rawHtml": stored,
        "rawHtmlHash": hashlib.sha256(encoded).hexdigest(),
        "rawHtmlBytes": len(encoded),
        "rawHtmlTruncated": truncated,
    }


def _page_priority(url: str, source: str, depth: int) -> tuple[int, int, str]:
    parsed = urlparse(url)
    path = parsed.path.lower().strip("/")
    if source == "homepage" or not path:
        return (0, depth, url)
    positive = [
        ("about", 10),
        ("service", 11),
        ("solution", 12),
        ("product", 13),
        ("pricing", 14),
        ("case", 15),
        ("work", 16),
        ("portfolio", 17),
        ("testimonial", 18),
        ("review", 19),
        ("contact", 20),
        ("book", 21),
        ("location", 22),
        ("industry", 23),
    ]
    negative = [
        "privacy",
        "terms",
        "cookie",
        "login",
        "wp-json",
        "tag",
        "author",
        "feed",
    ]
    if any(term in path for term in negative):
        return (90, depth, url)
    for term, score in positive:
        if term in path:
            return (score, depth, url)
    if source == "internal_link":
        return (45, depth, url)
    return (55, depth, url)


def _extract_page_summary(
    url: str, body: str, source: str, depth: int
) -> dict[str, Any]:
    signals = _parse_html(body)
    title = signals.title
    description = signals.meta_description
    primary_heading = signals.h1[0] if signals.h1 else None
    cta_text = signals.ctas[0] if signals.ctas else None

    summary_parts: list[str] = []
    citations: list[dict[str, Any]] = []

    if title:
        summary_parts.append(f"Title: {title}")
        citations.append(
            {
                "pageUrl": url,
                "evidenceType": "title",
                "label": "Page title",
                "excerpt": title,
                "confidence": 86,
            }
        )
    if description:
        summary_parts.append(f"Description: {description}")
        citations.append(
            {
                "pageUrl": url,
                "evidenceType": "meta",
                "label": "Meta description",
                "excerpt": description,
                "confidence": 80,
            }
        )
    if primary_heading:
        summary_parts.append(f"H1: {primary_heading}")
        citations.append(
            {
                "pageUrl": url,
                "evidenceType": "heading",
                "label": "Primary heading",
                "excerpt": primary_heading,
                "confidence": 76,
            }
        )
    if cta_text:
        citations.append(
            {
                "pageUrl": url,
                "evidenceType": "cta",
                "label": "CTA text",
                "excerpt": cta_text,
                "confidence": 78,
            }
        )

    sections = _normalize_sections(url, signals.sections)
    assets = _normalize_assets(url, signals.assets)
    if sections:
        citations.extend(
            {
                "pageUrl": url,
                "evidenceType": "section",
                "label": section.get("heading") or f"Section {section['index'] + 1}",
                "excerpt": section.get("text", "")[:220],
                "confidence": int(section.get("confidence", 55)),
            }
            for section in sections[:5]
            if section.get("text") or section.get("heading")
        )

    richness = sum(
        1 for value in [title, description, signals.h1[:1], cta_text, sections] if value
    )
    confidence = min(95, 35 + richness * 15 + min(len(citations), 3) * 4)
    errors: list[str] = []
    if not title:
        errors.append("title_missing")
    if not description and not signals.h1:
        errors.append("summary_sparse")

    return {
        "url": url,
        "source": source,
        "status": "crawled",
        "title": title,
        "summary": " | ".join(summary_parts) if summary_parts else None,
        "depth": depth,
        "ctaCount": len(signals.ctas),
        "confidence": confidence,
        "citations": citations,
        "errors": errors,
        "sections": sections,
        "assets": assets,
        **_raw_html_payload(body),
        "signals": signals,
    }


def _extract_brand_asset_cues(
    page_url: str, signals: PageSignals
) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    if signals.logo_candidates:
        cues.append(
            {
                "assetType": "logo",
                "label": "Logo candidate",
                "value": signals.logo_candidates[0],
                "sourceUrl": page_url,
                "confidence": 74,
                "note": "Detected from image metadata or filename.",
            }
        )
    if signals.theme_color:
        cues.append(
            {
                "assetType": "color",
                "label": "Theme color",
                "value": signals.theme_color,
                "sourceUrl": page_url,
                "confidence": 78,
                "note": "From meta theme-color.",
            }
        )
    if signals.images:
        cues.append(
            {
                "assetType": "image",
                "label": "Image asset reference",
                "value": signals.images[0],
                "sourceUrl": page_url,
                "confidence": 60,
                "note": "Public image or icon reference discovered on the page.",
            }
        )
    if signals.font_family:
        cues.append(
            {
                "assetType": "typography",
                "label": "Typography cue",
                "value": signals.font_family,
                "sourceUrl": page_url,
                "confidence": 52,
                "note": "Detected from font-family or font resource hints.",
            }
        )
    return cues


def _collect_audience_clues(text_chunks: Iterable[str]) -> list[str]:
    clues: list[str] = []
    joined = " ".join(text_chunks).lower()
    for phrase in [
        "for teams",
        "for businesses",
        "for startups",
        "for agencies",
        "for enterprises",
        "for homeowners",
        "for patients",
        "for contractors",
        "for founders",
        "for brands",
        "for developers",
        "for creators",
        "for marketers",
        "for retailers",
        "for platforms",
        "for saas",
        "for e-commerce",
        "for healthcare",
        "for finance",
        "for restaurants",
        "for freelancers",
        "for small business",
        "for professionals",
    ]:
        if phrase in joined:
            clues.append(phrase.title())
    return list(dict.fromkeys(clues))


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return cleaned[:80] or "capture"


def _capture_page_visuals(
    urls: list[str], *, crawl_id: str, lead_key: str | None
) -> dict[str, dict[str, Any]]:
    if not get_settings().extraction_enable_visual_capture:
        return {}
    try:
        sync_playwright = importlib.import_module("playwright.sync_api").sync_playwright
    except Exception:
        return {
            url: {"error": "playwright_not_installed", "sections": []} for url in urls
        }

    captures: dict[str, dict[str, Any]] = {}
    root = os.path.abspath(get_settings().asset_local_path)
    target_dir = os.path.join(
        root,
        "visual-captures",
        _safe_filename(lead_key or "lead"),
        _safe_filename(crawl_id),
    )
    os.makedirs(target_dir, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for page_index, url in enumerate(urls):
                base_name = (
                    f"{page_index:02d}-{_safe_filename(urlparse(url).path or 'home')}"
                )
                capture: dict[str, Any] = {"sections": []}
                try:
                    page = browser.new_page(
                        viewport={
                            "width": int(get_settings().extraction_screenshot_width),
                            "height": int(get_settings().extraction_screenshot_height),
                        }
                    )
                    page.goto(url, wait_until="networkidle", timeout=20000)
                    desktop_path = os.path.join(target_dir, f"{base_name}-desktop.png")
                    page.screenshot(path=desktop_path, full_page=True)
                    capture.update(
                        {
                            "desktopScreenshotUrl": desktop_path,
                            "capturedAt": datetime.now(timezone.utc).isoformat(),
                            "width": int(get_settings().extraction_screenshot_width),
                            "height": int(get_settings().extraction_screenshot_height),
                        }
                    )
                    eval_script = """
                    () => {
                        const getStyle = (el, prop) => window.getComputedStyle(el)[prop];
                        const sections = Array.from(document.querySelectorAll('header, main > section, section, article, footer'));
                        return {
                            meta: Array.from(document.querySelectorAll('meta')).reduce((acc, meta) => {
                                const name = meta.getAttribute('name') || meta.getAttribute('property');
                                if (name) acc[name] = meta.getAttribute('content');
                                return acc;
                            }, {}),
                            cleanedText: document.body ? document.body.innerText : "",
                            fonts: Array.from(new Set(Array.from(document.querySelectorAll('*')).map(el => getStyle(el, 'fontFamily')))),
                            colors: Array.from(new Set(Array.from(document.querySelectorAll('*')).map(el => getStyle(el, 'backgroundColor')).concat(Array.from(document.querySelectorAll('*')).map(el => getStyle(el, 'color'))))),
                            headings: Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(el => el.innerText),
                            links: Array.from(document.querySelectorAll('a')).map(el => el.href).filter(Boolean),
                            html: document.documentElement.outerHTML,
                            sectionsData: sections.map((sec, idx) => {
                                return {
                                    index: idx,
                                    html: sec.outerHTML,
                                    text: sec.innerText,
                                    computedStyles: {
                                        backgroundColor: getStyle(sec, 'backgroundColor'),
                                        color: getStyle(sec, 'color'),
                                        fontFamily: getStyle(sec, 'fontFamily'),
                                        padding: getStyle(sec, 'padding'),
                                        margin: getStyle(sec, 'margin'),
                                        fontSize: getStyle(sec, 'fontSize')
                                    }
                                };
                            })
                        };
                    }
                    """
                    page_data = page.evaluate(eval_script)
                    capture["pageData"] = page_data

                    section_limit = int(
                        get_settings().extraction_section_screenshot_limit or 0
                    )
                    if section_limit > 0:
                        locators = page.locator(
                            "header, main > section, section, article, footer"
                        )
                        count = min(locators.count(), section_limit)
                        for section_index in range(count):
                            locator = locators.nth(section_index)
                            box = locator.bounding_box()
                            if not box or box.get("height", 0) < 80:
                                continue
                            section_path = os.path.join(
                                target_dir,
                                f"{base_name}-section-{section_index:02d}.png",
                            )
                            locator.screenshot(path=section_path)
                            capture["sections"].append(
                                {
                                    "index": section_index,
                                    "screenshotUrl": section_path,
                                    "boundingBox": box,
                                }
                            )
                    page.set_viewport_size(
                        {
                            "width": int(
                                get_settings().extraction_mobile_screenshot_width
                            ),
                            "height": int(
                                get_settings().extraction_mobile_screenshot_height
                            ),
                        }
                    )
                    mobile_path = os.path.join(target_dir, f"{base_name}-mobile.png")
                    page.screenshot(path=mobile_path, full_page=True)
                    capture["mobileScreenshotUrl"] = mobile_path
                    page.close()
                except Exception as exc:
                    capture["error"] = str(exc)[:240]
                captures[url] = capture
            browser.close()
    except Exception as exc:
        return {url: {"error": str(exc)[:240], "sections": []} for url in urls}
    return captures


def crawl_website(
    website_url: str, *, lead_company_name: str | None = None
) -> dict[str, Any]:
    canonical_url, hostname = normalize_site_url(website_url)
    homepage_result = _safe_fetch(canonical_url)

    if not homepage_result["ok"]:
        return {
            "crawlStatus": "failed",
            "sitemapStatus": "unknown",
            "canonicalWebsiteUrl": canonical_url,
            "detectedWebsiteUrl": None,
            "pagesDiscovered": 0,
            "pagesCrawled": 0,
            "pageInventory": [],
            "sourceCitations": [],
            "brandAssetCues": [],
            "assetManifest": [],
            "sectionInventory": [],
            "visualCaptureSummary": {},
            "sitemapUrls": [],
            "confidenceScore": 0,
            "gapItems": ["homepage_unreachable"],
            "errors": [homepage_result["error"] or "homepage_fetch_failed"],
            "summary": {
                "companyName": lead_company_name,
                "canonicalWebsiteUrl": canonical_url,
                "detectedWebsiteUrl": None,
                "positioningSummary": None,
                "audienceClues": [],
                "serviceClues": [],
                "ctaClues": [],
                "toneClues": [],
            },
        }

    homepage_url = homepage_result["finalUrl"]
    homepage_signals = _parse_html(homepage_result["body"])
    detected_url = homepage_url if homepage_url != canonical_url else None
    sitemap_candidates = [
        urljoin(homepage_url, "/sitemap.xml"),
        urljoin(homepage_url, "/sitemap_index.xml"),
    ]
    sitemap_urls: list[str] = []
    sitemap_status = "missing"
    sitemap_errors: list[str] = []
    for sitemap_url in sitemap_candidates:
        sitemap_result = _safe_fetch(sitemap_url)
        if not sitemap_result["ok"]:
            sitemap_errors.append(sitemap_result["error"] or "sitemap_fetch_failed")
            continue
        parsed_urls = _parse_sitemap_urls(sitemap_result["body"] or "")
        if parsed_urls:
            sitemap_status = "found"
            sitemap_urls.extend(parsed_urls)
            if "sitemap_index" in sitemap_url:
                # Expand the first sitemap index layer so operators can see more than the top-level file.
                for nested_url in parsed_urls[:3]:
                    nested_result = _safe_fetch(nested_url)
                    if nested_result["ok"]:
                        sitemap_urls.extend(
                            _parse_sitemap_urls(nested_result["body"] or "")
                        )
            break
    sitemap_urls = [
        url for url in dict.fromkeys(sitemap_urls) if _same_origin(canonical_url, url)
    ]
    if sitemap_urls and sitemap_status != "found":
        sitemap_status = "found"
    if not sitemap_urls and sitemap_errors:
        sitemap_status = "error"

    discovered_urls: list[tuple[str, str, int]] = [(homepage_url, "homepage", 0)]
    homepage_links = []
    max_pages = _max_pages()
    if sitemap_urls:
        remaining = max_pages - 1
        for sitemap_url in sitemap_urls[:remaining]:
            discovered_urls.append((sitemap_url, "sitemap", 1))
        for href, anchor_text in homepage_signals.links:
            if not href:
                continue
            candidate = urljoin(homepage_url, href)
            if _same_origin(canonical_url, candidate):
                homepage_links.append(candidate)
    else:
        # No sitemap found, fall back to internal links
        for href, anchor_text in homepage_signals.links:
            if not href:
                continue
            candidate = urljoin(homepage_url, href)
            if _same_origin(canonical_url, candidate):
                homepage_links.append(candidate)
                # Only add to discovered_urls if we don't have sitemap
                if len(discovered_urls) < max_pages:
                    discovered_urls.append((candidate, "internal_link", 1))
    discovered_map: dict[str, tuple[str, str, int]] = {}
    for url, source, depth in discovered_urls:
        discovered_map.setdefault(url, (url, source, depth))

    ordered_candidates = sorted(
        discovered_map.values(),
        key=lambda item: _page_priority(item[0], item[1], item[2]),
    )[: _max_pages()]
    # Crawl budget and timing
    crawl_start = time.time()
    crawl_id = f"crawl-{uuid.uuid4().hex}"
    total_bytes_downloaded = 0
    downloader = AssetDownloader()
    page_inventory: list[dict[str, Any]] = []
    source_citations: list[dict[str, Any]] = []
    brand_asset_cues: list[dict[str, Any]] = []
    asset_manifest: list[dict[str, Any]] = []
    section_inventory: list[dict[str, Any]] = []
    visual_capture_summary = {
        "pagesAttempted": 0,
        "pagesCaptured": 0,
        "sectionsCaptured": 0,
        "errors": 0,
    }
    service_clues: list[str] = []
    cta_clues: list[str] = []
    tone_clues: list[str] = []
    body_text_for_audience: list[str] = []
    crawled_count = 0

    for url, source, depth in ordered_candidates:
        # time budget enforcement
        elapsed = time.time() - crawl_start
        if elapsed > settings.crawl_time_limit_seconds:
            # stop crawling due to time budget
            break
        # estimated page size heuristic to check budget
        estimated_page_size = 50_000
        if not downloader.enforce_aggregate_limit(
            total_bytes_downloaded + estimated_page_size, settings.crawl_budget_bytes
        ):
            # stop due to crawl budget
            break
        result = _safe_fetch(url)
        if not result["ok"]:
            page_inventory.append(
                {
                    "url": url,
                    "source": source,
                    "status": "failed",
                    "title": None,
                    "summary": None,
                    "depth": depth,
                    "ctaCount": 0,
                    "confidence": 0,
                    "citations": [],
                    "errors": [result["error"] or "fetch_failed"],
                }
            )
            continue

        crawled_count += 1
        page_data = _extract_page_summary(url, result["body"] or "", source, depth)
        signals: PageSignals = page_data.pop("signals")

        # Enrich with Playwright pageData if available
        if result.get("renderedByPlaywright") and result.get("pageData"):
            pw_data = result["pageData"]
            page_data["renderedByPlaywright"] = True
            page_data["meta"] = pw_data.get("meta", {})
            page_data["cleanedText"] = pw_data.get("cleanedText", "")
            page_data["fonts"] = pw_data.get("fonts", [])
            page_data["colors"] = list(set(pw_data.get("colors", [])))
            page_data["headings"] = pw_data.get("headings", [])
            page_data["playwrightLinks"] = pw_data.get("links", [])
            page_data["playwrightImages"] = pw_data.get("images", [])

            # Enrich sections with Playwright-extracted data
            pw_sections = pw_data.get("sectionsData", [])
            for section in page_data.get("sections", []):
                section_index = section.get("index")
                pw_section = next(
                    (s for s in pw_sections if s.get("index") == section_index), None
                )
                if pw_section:
                    section["html"] = pw_section.get("html", "")
                    section["text"] = pw_section.get("text", section.get("text", ""))
                    section["playwrightHeadings"] = pw_section.get("headings", [])
                    section["playwrightCtas"] = pw_section.get("ctas", [])
                    section["computedStyles"] = pw_section.get("computedStyles", {})
                    if pw_section.get("images"):
                        section["imageUrls"] = list(
                            dict.fromkeys(
                                section.get("imageUrls", []) + pw_section["images"]
                            )
                        )

        page_inventory.append(page_data)
        source_citations.extend(page_data["citations"])
        for asset in page_data.get("assets", []):
            if asset not in asset_manifest:
                asset_manifest.append(asset)
        for section in page_data.get("sections", []):
            section_inventory.append({**section, "pageUrl": url})

        if page_data.get("sections"):
            logger.info(f"Extracted {len(page_data['sections'])} sections from {url}")
        brand_asset_cues.extend(_extract_brand_asset_cues(url, signals))
        if url == homepage_url:
            asset_urls = [
                value
                for cue in brand_asset_cues
                for value in [cue.get("value")]
                if cue.get("assetType") in {"logo", "image", "typography"}
                and isinstance(value, str)
                and value.startswith("http")
            ]
            if asset_urls and settings.asset_download_enabled:
                try:
                    lead_id_for_download = lead_company_name or "unknown"
                    dl_results = asyncio.run(
                        downloader.download_batch(asset_urls, lead_id_for_download)
                    )
                    for result_item in dl_results:
                        for cue in brand_asset_cues:
                            if cue.get("value") != result_item.source_url:
                                continue
                            if not result_item.success:
                                cue.setdefault("note", "")
                                cue["note"] = (
                                    cue.get("note") or ""
                                ) + f";download_error:{result_item.error}"
                                continue

                            try:
                                asyncio.run(
                                    asset_metadata.reserve_crawl_budget(
                                        crawl_id,
                                        int(result_item.bytes or 0),
                                        settings.crawl_budget_bytes,
                                    )
                                )
                            except Exception:
                                if result_item.cached_uri:
                                    try:
                                        downloader.storage.delete(
                                            result_item.cached_uri
                                        )
                                    except Exception:
                                        pass
                                cue.setdefault("note", "")
                                cue["note"] = (
                                    cue.get("note") or ""
                                ) + ";download_error:budget_exceeded"
                                continue

                            doc = {
                                "leadId": lead_company_name or "unknown",
                                "sourceUrl": result_item.source_url,
                                "cachedUri": result_item.cached_uri,
                                "cachedAt": result_item.cached_at,
                                "expiresAt": result_item.expires_at,
                                "bytes": int(result_item.bytes or 0),
                                "checksum": result_item.checksum,
                                "contentType": result_item.content_type,
                                "pinned": False,
                                "error": None,
                            }
                            try:
                                asyncio.run(asset_metadata.create_asset_doc(doc))
                            except Exception:
                                if result_item.cached_uri:
                                    try:
                                        downloader.storage.delete(
                                            result_item.cached_uri
                                        )
                                    except Exception:
                                        pass
                                cue.setdefault("note", "")
                                cue["note"] = (
                                    cue.get("note") or ""
                                ) + ";metadata_error"
                                continue

                            cue["cachedUri"] = result_item.cached_uri
                            cue["cachedAt"] = (
                                result_item.cached_at.isoformat()
                                if result_item.cached_at
                                else None
                            )
                            cue["expiresAt"] = (
                                result_item.expires_at.isoformat()
                                if result_item.expires_at
                                else None
                            )
                            cue["bytes"] = result_item.bytes
                            cue["checksum"] = result_item.checksum
                            total_bytes_downloaded += result_item.bytes or 0
                    if total_bytes_downloaded > settings.crawl_budget_bytes:
                        break
                except Exception as e:
                    logger.warning(f"Asset download failed: {e}")
            if url == homepage_url:
                if signals.h1:
                    service_clues.extend(signals.h1[:2])
                if signals.h2:
                    service_clues.extend(signals.h2[:4])
            else:
                if signals.h1:
                    service_clues.extend(signals.h1[:1])
                if signals.h2:
                    service_clues.extend(signals.h2[:2])

            for section in page_data.get("sections", []):
                if section.get("type") == "services":
                    heading = section.get("heading")
                    if heading and heading not in service_clues:
                        service_clues.append(heading)
                    section_text = section.get("text") or ""
                    for line in section_text.split("\n")[:5]:
                        line = line.strip()
                        if 3 < len(line) < 60 and line[0].isupper():
                            service_clues.append(line)

            if signals.ctas:
                cta_clues.extend(signals.ctas[:3])
            body_text_for_audience.extend(signals.body_text[:10])
            if signals.meta_description:
                body_text_for_audience.append(signals.meta_description)
            if signals.title:
                body_text_for_audience.append(signals.title)
            if signals.font_family:
                tone_clues.append("Typography cue detected from public font hints.")

    crawled_urls = [
        item["url"] for item in page_inventory if item.get("status") == "crawled"
    ]
    if crawled_urls:
        captures = _capture_page_visuals(
            crawled_urls,
            crawl_id=crawl_id,
            lead_key=lead_company_name or hostname,
        )
        for item in page_inventory:
            capture = captures.get(item["url"])
            if not capture:
                continue

            page_data = capture.get("pageData", {})
            if page_data:
                item["meta"] = page_data.get("meta", {})
                item["cleanedText"] = page_data.get("cleanedText", "")
                item["fonts"] = page_data.get("fonts", [])
                item["colors"] = list(set(page_data.get("colors", [])))
                item["headings"] = page_data.get("headings", [])
                item["links"] = page_data.get("links", [])
                item["rawHtmlRef"] = item.get("rawHtmlHash")

                section_data_map = {
                    s.get("index"): s for s in page_data.get("sectionsData", [])
                }
                for section in item.get("sections", []):
                    sd = section_data_map.get(section.get("index"))
                    if sd:
                        section["html"] = sd.get("html")
                        section["computedStyles"] = sd.get("computedStyles")
                        if sd.get("text"):
                            section["text"] = sd.get("text")

            visual_capture_summary["pagesAttempted"] += 1
            if capture.get("error"):
                visual_capture_summary["errors"] += 1
            if capture.get("desktopScreenshotUrl"):
                visual_capture_summary["pagesCaptured"] += 1
            visual_capture_summary["sectionsCaptured"] += len(
                capture.get("sections", [])
            )
            item["visualCapture"] = {
                "desktopScreenshotUrl": capture.get("desktopScreenshotUrl"),
                "mobileScreenshotUrl": capture.get("mobileScreenshotUrl"),
                "capturedAt": capture.get("capturedAt"),
                "width": capture.get("width"),
                "height": capture.get("height"),
                "error": capture.get("error"),
            }
            section_captures = {
                section.get("index"): section for section in capture.get("sections", [])
            }
            for section in item.get("sections", []):
                section_capture = section_captures.get(section.get("index"))
                if section_capture:
                    section["screenshotUrl"] = section_capture.get("screenshotUrl")
                    section["boundingBox"] = section_capture.get("boundingBox")
        section_inventory = [
            {**section, "pageUrl": item["url"]}
            for item in page_inventory
            for section in item.get("sections", [])
        ]

    page_urls = [item["url"] for item in page_inventory]
    pages_discovered = len(page_urls)
    pages_crawled = crawled_count
    if page_urls:
        logger.info(
            "Crawled %s pages (%s discovered): %s",
            pages_crawled,
            pages_discovered,
            ", ".join(page_urls),
        )
    confidence_score = 0
    if page_inventory:
        confidence_score = min(
            95,
            round(
                sum(item["confidence"] for item in page_inventory) / len(page_inventory)
            ),
        )
    if homepage_signals.meta_description:
        confidence_score = min(95, confidence_score + 5)
    if sitemap_status == "found":
        confidence_score = min(95, confidence_score + 5)

    gaps: list[str] = []
    if sitemap_status in {"missing", "error"}:
        gaps.append("sitemap_unavailable")
    if not brand_asset_cues:
        gaps.append("brand_assets_missing")
    if (
        all(item["confidence"] < 60 for item in page_inventory)
        if page_inventory
        else True
    ):
        gaps.append("low_confidence_extraction")
    if not any(item["summary"] for item in page_inventory):
        gaps.append("page_summaries_sparse")
    if not section_inventory:
        gaps.append("section_structure_sparse")
    if not asset_manifest:
        gaps.append("asset_manifest_sparse")

    errors = list(
        dict.fromkeys(
            [
                *sitemap_errors,
                *[error for item in page_inventory for error in item.get("errors", [])],
            ]
        )
    )

    service_clues = list(dict.fromkeys(service_clues[:12]))
    cta_clues = list(dict.fromkeys(cta_clues[:4]))
    tone_clues = list(dict.fromkeys(tone_clues))
    audience_clues = _collect_audience_clues(body_text_for_audience)
    if not audience_clues and homepage_signals.meta_description:
        audience_clues.append(
            "Audience not explicit in public metadata; review manually."
        )

    positioning_summary = None
    if homepage_signals.title or homepage_signals.meta_description:
        parts = []
        if homepage_signals.title:
            parts.append(f"Homepage title: {homepage_signals.title}")
        if homepage_signals.meta_description:
            parts.append(f"Meta description: {homepage_signals.meta_description}")
        positioning_summary = " ".join(parts)

    summary = {
        "companyName": lead_company_name,
        "canonicalWebsiteUrl": canonical_url,
        "detectedWebsiteUrl": detected_url,
        "positioningSummary": positioning_summary,
        "audienceClues": audience_clues,
        "serviceClues": service_clues,
        "ctaClues": cta_clues,
        "toneClues": tone_clues,
    }

    crawl_status: str
    if pages_crawled == 0:
        crawl_status = "failed"
    elif gaps:
        crawl_status = "partial"
    else:
        crawl_status = "completed"

    asset_cache_stats: dict[str, int] = {}
    for cue in brand_asset_cues:
        t = cue.get("assetType") or "unknown"
        if cue.get("cachedUri"):
            asset_cache_stats[t] = asset_cache_stats.get(t, 0) + 1

    logger.info(
        f"Crawl complete: {pages_crawled} pages crawled, {pages_discovered} discovered, "
        f"status={crawl_status}, sitemap={sitemap_status}"
    )

    return {
        "crawlStatus": crawl_status,
        "sitemapStatus": sitemap_status,
        "canonicalWebsiteUrl": canonical_url,
        "detectedWebsiteUrl": detected_url,
        "pagesDiscovered": pages_discovered,
        "pagesCrawled": pages_crawled,
        "pageInventory": page_inventory,
        "sourceCitations": source_citations,
        "brandAssetCues": brand_asset_cues,
        "assetManifest": asset_manifest[:120],
        "sectionInventory": section_inventory[:80],
        "visualCaptureSummary": visual_capture_summary,
        "sitemapUrls": sitemap_urls,
        "confidenceScore": confidence_score,
        "gapItems": gaps,
        "errors": errors,
        "summary": summary,
        "assetCacheStats": asset_cache_stats,
        "crawlBudgetUsed": total_bytes_downloaded,
        "crawlBudgetLimit": settings.crawl_budget_bytes,
        "crawlTimeElapsedSeconds": int(time.time() - crawl_start),
    }
