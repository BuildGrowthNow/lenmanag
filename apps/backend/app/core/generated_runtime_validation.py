"""Security and contract checks for provider-generated browser JavaScript."""

from __future__ import annotations

import re


_INLINE_SCRIPT_PATTERN = re.compile(
    r"<script\b([^>]*)>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL
)
_SCRIPT_TAG_PATTERN = re.compile(r"<script\b([^>]*)/?>", re.IGNORECASE | re.DOTALL)
_INLINE_HANDLER_PATTERN = re.compile(
    r"\bon[a-z][a-z0-9_-]*\s*=\s*(['\"])", re.IGNORECASE
)


_FORBIDDEN_RUNTIME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("eval()", re.compile(r"\beval\s*\(")),
    ("Function()", re.compile(r"\bFunction\s*\(")),
    ("dynamic imports", re.compile(r"\bimport\s*\(")),
    ("require()", re.compile(r"\brequire\s*\(")),
    ("fetch()", re.compile(r"\bfetch\s*\(")),
    ("XMLHttpRequest", re.compile(r"\bXMLHttpRequest\b")),
    ("WebSocket", re.compile(r"\bWebSocket\b")),
    ("EventSource", re.compile(r"\bEventSource\b")),
    ("Worker", re.compile(r"\b(?:SharedWorker|Worker)\b")),
    ("BroadcastChannel", re.compile(r"\bBroadcastChannel\b")),
    (
        "browser storage",
        re.compile(r"\b(?:localStorage|sessionStorage|indexedDB)\b"),
    ),
    ("sendBeacon()", re.compile(r"\b(?:navigator\s*\.\s*)?sendBeacon\s*\(")),
    (
        "document cookie/domain/location/write",
        re.compile(r"\bdocument\s*\.\s*(?:cookie|domain|location|write)\b"),
    ),
    (
        "parent-window access",
        re.compile(r"\bwindow\s*\.\s*(?:parent|top|opener|frames|open)\b"),
    ),
    (
        "location navigation",
        re.compile(r"\b(?:window\s*\.\s*)?location\s*\.\s*(?:href|assign|replace)\b"),
    ),
    (
        "service-worker/cache access",
        re.compile(r"\b(?:navigator\s*\.\s*serviceWorker|caches\s*\.)"),
    ),
    (
        "string-based timers",
        re.compile(r"\b(?:setTimeout|setInterval)\s*\(\s*['\"]"),
    ),
)


def validate_generated_javascript(source: str) -> list[str]:
    """Return deterministic security errors for a static generated runtime.

    This remains the last gate before publication for both compiled static
    entries and test/local fallback artifacts. It mirrors the compiler's
    browser API restrictions and intentionally reports rule names instead of
    source text so rejected provider output is not echoed into logs or prompts.
    """

    errors: list[str] = []
    for label, pattern in _FORBIDDEN_RUNTIME_PATTERNS:
        if pattern.search(source):
            errors.append(f"Forbidden generated JavaScript API: {label}")
    return errors


def validate_generated_html(source: str) -> list[str]:
    """Reject executable provider HTML outside the dedicated JS artifact.

    JSON-LD is intentionally allowed because it is metadata, not executable
    code. Every other script must be supplied by the trusted runtime bundler;
    allowing provider-authored inline scripts or event attributes would make
    the separate JavaScript validator ineffective.
    """
    errors: list[str] = []
    if _INLINE_HANDLER_PATTERN.search(source):
        errors.append("Generated HTML contains an inline event handler")

    for match in _SCRIPT_TAG_PATTERN.finditer(source):
        attrs = match.group(1) or ""
        script_type = re.search(
            r"\btype\s*=\s*(['\"])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL
        )
        normalized_type = script_type.group(2).strip().lower() if script_type else ""
        if normalized_type == "application/ld+json":
            continue
        errors.append(
            "Generated HTML may not contain executable script tags; use the dedicated JS artifact"
        )
        break

    for match in _INLINE_SCRIPT_PATTERN.finditer(source):
        attrs = match.group(1) or ""
        script_type = re.search(
            r"\btype\s*=\s*(['\"])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL
        )
        normalized_type = script_type.group(2).strip().lower() if script_type else ""
        if normalized_type == "application/ld+json":
            continue
        if match.group(2).strip():
            errors.append("Generated HTML contains inline executable script content")
            break
    return errors
