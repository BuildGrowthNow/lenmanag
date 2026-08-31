import json

import pytest

from app.core.asset_utils import get_best_asset_url
from app.core.site_screenshot import _fatal_runtime_failures
from app.core.static_html_generator import (
    _enforce_footer_year,
    _javascript_is_valid,
    _parse_llm_response,
    _remove_generated_asset_references,
    _validate_generated_document,
)
from app.core.extraction import _extract_contact_info
from datetime import datetime, timezone


def test_truncated_javascript_is_rejected() -> None:
    with pytest.raises(ValueError, match="Expected closed"):
        _parse_llm_response("```html\n<!DOCTYPE html><html><head></head><body></body></html>\n```\n```css\na{}\n```\n```javascript\nconst x =")


def test_invalid_javascript_never_validates_for_upload() -> None:
    assert not _javascript_is_valid("document.addEventListener('x', () => {")


def test_relative_generated_asset_references_are_removed() -> None:
    html = '<html><head><link rel="stylesheet" href="/st/demo/styles.css"></head><body><script src="./script.js"></script></body></html>'
    cleaned = _remove_generated_asset_references(html)
    assert "styles.css" not in cleaned and "script.js" not in cleaned


def test_page_url_cannot_become_logo_and_relative_asset_resolves() -> None:
    assert get_best_asset_url({"assetUrl": "https://example.test/", "sourceUrl": "https://example.test/"}) is None
    assert get_best_asset_url({"value": "/assets/brand.svg", "pageUrl": "https://example.test/about"}) == "https://example.test/assets/brand.svg"


def test_fatal_runtime_health_blocks_readiness() -> None:
    failures = _fatal_runtime_failures({"pageErrors": ["SyntaxError"], "readiness": False, "mainContentRendered": True})
    assert "page_errors" in failures and "readiness_missing_or_false" in failures


def test_document_requires_closed_structure() -> None:
    with pytest.raises(ValueError):
        _validate_generated_document("<!DOCTYPE html><html><head></head><body>", "a{}", "const a = 1;")


def test_footer_year_is_current_but_historic_year_is_preserved() -> None:
    year = str(datetime.now(timezone.utc).year)
    html = "<p>Since 1989</p><footer>© 2024 Example</footer>"
    result = _enforce_footer_year(html)
    assert "Since 1989" in result and f"© {year}" in result


def test_extracted_contact_info_keeps_real_office_and_emergency_numbers() -> None:
    contacts = _extract_contact_info([{"url": "https://example.test/contact", "cleanedText": "Emergency +1 574-849-6188 Office +1 574-862-4253"}])
    assert contacts["emergencyPhone"].endswith("6188")
    assert contacts["officePhone"].endswith("4253")
