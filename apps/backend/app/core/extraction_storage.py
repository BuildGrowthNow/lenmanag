"""Keep large page builder extracts within MongoDB's document limit."""

from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any

from bson import BSON
from bs4 import BeautifulSoup


MAX_EXTRACTION_BYTES = 12_000_000


def compact_extraction_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    """Trim redundant diagnostics only when the complete snapshot is oversized."""
    if len(BSON.encode(payload)) <= MAX_EXTRACTION_BYTES:
        return payload

    compact = deepcopy(payload)
    for page in compact.get("pageInventory", []):
        raw = page.get("rawHtml")
        if raw:
            soup = BeautifulSoup(raw, "html.parser")
            # Keep attribution context so a designer's footer email remains
            # distinguishable from a business contact after HTML truncation.
            contacts = "\n".join(
                "<div>" + escape(a.parent.get_text(" ", strip=True)[:3_000]) + str(a) + "</div>"
                for a in soup.select('a[href^="tel:"], a[href^="mailto:"]')
            )
            for node in soup(["script", "style", "noscript"]):
                node.decompose()
            page["rawHtml"] = contacts + "\n" + str(soup)[:100_000]
            page["rawHtmlTruncated"] = True

    list_limits = {
        "links": 300, "playwrightLinks": 300, "playwrightImages": 120,
        "assets": 120, "sections": 80, "sectionInventory": 80,
        "sitemapUrls": 500, "sourceCitations": 500, "citations": 40,
        "imageUrls": 120, "assetUrls": 120,
    }
    text_limits = {"html": 2_000, "cleanedText": 20_000, "text": 3_000}

    def trim(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {name: trim(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [trim(item, key) for item in value[:list_limits.get(key, len(value))]]
        if isinstance(value, str):
            if value.startswith("data:") and len(value) > 10_000:
                return ""
            return value[:text_limits.get(key, len(value))]
        return value

    compact = trim(compact)
    if len(BSON.encode(compact)) > MAX_EXTRACTION_BYTES:
        raise ValueError("Extraction remains too large after diagnostic compaction")
    return compact
