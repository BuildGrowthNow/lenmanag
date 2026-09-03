"""Runtime checks for the interaction contract emitted by generated sites."""

from __future__ import annotations

from typing import Any


def normalize_interaction_manifest(value: Any) -> list[dict[str, Any]]:
    """Keep only safe, executable interaction declarations from page data."""
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        selector = item.get("selector")
        action = item.get("action", "click")
        if not isinstance(selector, str) or not selector.strip():
            continue
        if action not in {"click", "press"}:
            continue
        result.append(
            {
                "id": str(item.get("id") or f"interaction-{index + 1}"),
                "selector": selector,
                "action": action,
                "key": str(item.get("key") or "Enter"),
                "required": item.get("required", True) is not False,
            }
        )
    return result


def interaction_state(page: Any, selector: str) -> dict[str, Any]:
    """Capture observable state that should change after an interaction."""
    return page.locator(selector).first.evaluate(
        """el => ({
          text: (el.innerText || '').slice(0, 500),
          expanded: el.getAttribute('aria-expanded'),
          pressed: el.getAttribute('aria-pressed'),
          state: el.getAttribute('data-state'),
          hidden: el.hidden || getComputedStyle(el).display === 'none',
          target: el.getAttribute('href') || el.getAttribute('data-target') || '',
          accessibility: {
            role: el.getAttribute('role') || el.tagName.toLowerCase(),
            label: el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || '',
            tabIndex: el.tabIndex,
            disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true'
          }
        })"""
    )


def state_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return any(before.get(key) != after.get(key) for key in before)


def run_interaction_manifest(
    page: Any, manifest: Any, *, viewport: str = "desktop"
) -> list[dict[str, Any]]:
    """Execute declared interactions and return structured pass/fail records."""
    results: list[dict[str, Any]] = []
    for item in normalize_interaction_manifest(manifest):
        record = {
            "id": item["id"],
            "selector": item["selector"],
            "action": item["action"],
            "inputMethod": "keyboard" if item["action"] == "press" else "pointer",
            "viewport": viewport,
            "required": item["required"],
        }
        try:
            locator = page.locator(item["selector"]).first
            if locator.count() == 0:
                raise ValueError("selector_not_found")
            before = interaction_state(page, item["selector"])
            if item["action"] == "press":
                locator.press(item["key"])
            else:
                locator.click()
            page.wait_for_timeout(100)
            after = interaction_state(page, item["selector"])
            record["initialState"] = before
            record["finalState"] = after
            record["accessibilityState"] = after.get("accessibility", {})
            record["passed"] = state_changed(before, after)
            if not record["passed"]:
                record["error"] = "interaction_did_not_change_observable_state"
        except Exception as exc:
            record["passed"] = False
            record["error"] = str(exc)[:300]
        results.append(record)
    return results
