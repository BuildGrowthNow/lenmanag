from __future__ import annotations

import re
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


USER_AGENT = "LenQuantBot/0.3 (+internal extraction)"
MAX_PAGES = 6
FETCH_TIMEOUT = 12


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
    ctas: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)
    logo_candidates: list[str] = field(default_factory=list)
    body_text: list[str] = field(default_factory=list)


class _SignalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.signals = PageSignals()
        self._current_tag: str | None = None
        self._text_buffer: list[str] = []
        self._text_target: str | None = None
        self._in_style = False
        self._style_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs}
        self._current_tag = tag.lower()

        if self._current_tag in {"title", "h1", "h2", "p", "li", "button", "a", "strong", "em", "span"}:
            self._text_target = self._current_tag
            self._text_buffer = []

        if self._current_tag == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            content = attr_map.get("content") or ""
            if name in {"description", "og:description"} and content and not self.signals.meta_description:
                self.signals.meta_description = content.strip()
            if name in {"theme-color", "msapplication-tilecolor"} and content and not self.signals.theme_color:
                self.signals.theme_color = content.strip()
            if name in {"og:image", "twitter:image"} and content:
                self.signals.images.append(content.strip())

        if self._current_tag == "link":
            rel = (attr_map.get("rel") or "").lower()
            href = attr_map.get("href") or ""
            if rel == "canonical" and href and not self.signals.canonical_url:
                self.signals.canonical_url = href.strip()
            if rel in {"icon", "shortcut icon", "apple-touch-icon"} and href:
                self.signals.images.append(href.strip())
            if "font" in rel and href:
                self.signals.font_family = href.strip()

        if self._current_tag == "img":
            src = attr_map.get("src") or ""
            alt = attr_map.get("alt") or ""
            title = attr_map.get("title") or ""
            candidate = src.strip() or alt.strip() or title.strip()
            if candidate:
                self.signals.images.append(candidate)
            hint = f"{alt} {title} {src}".lower()
            if "logo" in hint:
                self.signals.logo_candidates.append(candidate or src.strip())

        if self._current_tag in {"a", "button"}:
            href = attr_map.get("href") or ""
            self.signals.links.append((href.strip(), ""))
            class_text = " ".join(filter(None, [attr_map.get("class"), attr_map.get("id")])).lower()
            if "cta" in class_text or "btn" in class_text or "button" in class_text:
                self._text_target = "cta"
                self._text_buffer = []

        if self._current_tag == "style":
            self._in_style = True
            self._style_chunks = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._text_target:
            self._text_buffer.append(text)
        elif self._current_tag in {"body", "main", "section", "article"}:
            self.signals.body_text.append(text)
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
            elif tag == "h2" and text:
                self.signals.h2.append(text)
            elif tag in {"a", "button"} and text:
                if self.signals.links:
                    href, _ = self.signals.links[-1]
                    self.signals.links[-1] = (href, text)
                if self._text_target == "cta" or _looks_like_cta(text):
                    self.signals.ctas.append(text)
            elif text:
                self.signals.body_text.append(text)
            self._text_target = None
            self._text_buffer = []

        if tag == "style" and self._in_style:
            style_text = " ".join(self._style_chunks)
            if not self.signals.font_family:
                font_match = re.search(r"font-family\s*:\s*([^;]+)", style_text, re.IGNORECASE)
                if font_match:
                    self.signals.font_family = font_match.group(1).strip().strip("\"'")
            self._in_style = False
            self._style_chunks = []


def _looks_like_cta(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["contact", "get started", "book", "demo", "quote", "learn more", "consult", "talk", "call", "schedule"])


def _fetch_url(url: str) -> tuple[str, str, dict[str, str]]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    context = ssl.create_default_context()
    with urlopen(request, timeout=FETCH_TIMEOUT, context=context) as response:
        body = response.read().decode("utf-8", errors="replace")
        final_url = response.geturl()
        headers = {key.lower(): value for key, value in response.headers.items()}
        return body, final_url, headers


def _safe_fetch(url: str) -> dict[str, Any]:
    try:
        body, final_url, headers = _fetch_url(url)
        return {"ok": True, "body": body, "finalUrl": final_url, "headers": headers, "error": None}
    except HTTPError as exc:
        return {"ok": False, "body": None, "finalUrl": url, "headers": {}, "error": f"http_{exc.code}"}
    except URLError as exc:
        return {"ok": False, "body": None, "finalUrl": url, "headers": {}, "error": f"url_{getattr(exc, 'reason', 'fetch_failed')}"}
    except Exception as exc:  # pragma: no cover - network edge cases
        return {"ok": False, "body": None, "finalUrl": url, "headers": {}, "error": str(exc)}


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


def _same_origin(base_url: str, candidate: str) -> bool:
    base = urlparse(base_url)
    candidate_parsed = urlparse(candidate)
    return bool(candidate_parsed.scheme in {"http", "https"} and candidate_parsed.hostname and candidate_parsed.hostname == base.hostname)


def _guess_page_source(url: str, homepage_url: str, sitemap_urls: set[str]) -> str:
    if url == homepage_url:
        return "homepage"
    if url in sitemap_urls:
        return "sitemap"
    return "internal_link"


def _extract_page_summary(url: str, body: str, source: str, depth: int) -> dict[str, Any]:
    signals = _parse_html(body)
    title = signals.title
    description = signals.meta_description
    cta_text = next((cta for cta in signals.ctas if cta), None)
    summary_parts: list[str] = []
    if title:
        summary_parts.append(f"Title: {title}")
    if description:
        summary_parts.append(f"Description: {description}")
    if signals.h1:
        summary_parts.append(f"H1: {signals.h1[0]}")
    if cta_text:
        summary_parts.append(f"CTA: {cta_text}")
    if not summary_parts and signals.body_text:
        summary_parts.append(f"Body: {signals.body_text[0]}")

    citations: list[dict[str, Any]] = []
    if title:
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
        citations.append(
            {
                "pageUrl": url,
                "evidenceType": "meta",
                "label": "Meta description",
                "excerpt": description,
                "confidence": 80,
            }
        )
    if signals.h1:
        citations.append(
            {
                "pageUrl": url,
                "evidenceType": "heading",
                "label": "Primary heading",
                "excerpt": signals.h1[0],
                "confidence": 82,
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

    richness = sum(1 for value in [title, description, signals.h1[:1], cta_text] if value)
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
        "signals": signals,
    }


def _extract_brand_asset_cues(page_url: str, signals: PageSignals) -> list[dict[str, Any]]:
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
    ]:
        if phrase in joined:
            clues.append(phrase.title())
    return list(dict.fromkeys(clues))


def crawl_website(website_url: str, *, lead_company_name: str | None = None) -> dict[str, Any]:
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
                        sitemap_urls.extend(_parse_sitemap_urls(nested_result["body"] or ""))
            break
    sitemap_urls = [url for url in dict.fromkeys(sitemap_urls) if _same_origin(canonical_url, url)]
    if sitemap_urls and sitemap_status != "found":
        sitemap_status = "found"
    if not sitemap_urls and sitemap_errors:
        sitemap_status = "error"

    discovered_urls: list[tuple[str, str, int]] = [(homepage_url, "homepage", 0)]
    homepage_links = []
    for href, anchor_text in homepage_signals.links:
        if not href:
            continue
        candidate = urljoin(homepage_url, href)
        if _same_origin(canonical_url, candidate):
            homepage_links.append(candidate)
            discovered_urls.append((candidate, "internal_link", 1))
    for sitemap_url in sitemap_urls:
        discovered_urls.append((sitemap_url, "sitemap", 1))
    discovered_map: dict[str, tuple[str, str, int]] = {}
    for url, source, depth in discovered_urls:
        discovered_map.setdefault(url, (url, source, depth))

    ordered_candidates = list(discovered_map.values())[:MAX_PAGES]
    page_inventory: list[dict[str, Any]] = []
    source_citations: list[dict[str, Any]] = []
    brand_asset_cues: list[dict[str, Any]] = []
    service_clues: list[str] = []
    cta_clues: list[str] = []
    tone_clues: list[str] = []
    body_text_for_audience: list[str] = []
    crawled_count = 0

    for url, source, depth in ordered_candidates:
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
        page_inventory.append(page_data)
        source_citations.extend(page_data["citations"])
        if url == homepage_url:
            brand_asset_cues.extend(_extract_brand_asset_cues(url, signals))
            if signals.h1:
                service_clues.extend(signals.h1[:2])
            if signals.ctas:
                cta_clues.extend(signals.ctas[:3])
            body_text_for_audience.extend(signals.body_text[:10])
            if signals.meta_description:
                body_text_for_audience.append(signals.meta_description)
            if signals.title:
                body_text_for_audience.append(signals.title)
            if signals.font_family:
                tone_clues.append("Typography cue detected from public font hints.")

    page_urls = [item["url"] for item in page_inventory]
    pages_discovered = len(page_urls)
    pages_crawled = crawled_count
    confidence_score = 0
    if page_inventory:
        confidence_score = min(95, round(sum(item["confidence"] for item in page_inventory) / len(page_inventory)))
    if homepage_signals.meta_description:
        confidence_score = min(95, confidence_score + 5)
    if sitemap_status == "found":
        confidence_score = min(95, confidence_score + 5)

    gaps: list[str] = []
    if sitemap_status in {"missing", "error"}:
        gaps.append("sitemap_unavailable")
    if not brand_asset_cues:
        gaps.append("brand_assets_missing")
    if all(item["confidence"] < 60 for item in page_inventory) if page_inventory else True:
        gaps.append("low_confidence_extraction")
    if not any(item["summary"] for item in page_inventory):
        gaps.append("page_summaries_sparse")

    errors = list(dict.fromkeys([*sitemap_errors, *[error for item in page_inventory for error in item.get("errors", [])]]))

    service_clues = list(dict.fromkeys(service_clues[:4]))
    cta_clues = list(dict.fromkeys(cta_clues[:4]))
    tone_clues = list(dict.fromkeys(tone_clues))
    audience_clues = _collect_audience_clues(body_text_for_audience)
    if not audience_clues and homepage_signals.meta_description:
        audience_clues.append("Audience not explicit in public metadata; review manually.")

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
        "sitemapUrls": sitemap_urls,
        "confidenceScore": confidence_score,
        "gapItems": gaps,
        "errors": errors,
        "summary": summary,
    }

