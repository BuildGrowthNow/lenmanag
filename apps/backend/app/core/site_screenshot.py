"""
Screenshot capture module for generated sites.

Captures above-the-fold viewport screenshots of preview URLs using
Playwright and uploads them to S3. Returns SiteScreenshotMetadata
on success, None on any failure (never crashes the caller).
"""

from __future__ import annotations

import importlib
import logging
import os
import json
from urllib.parse import urljoin
from datetime import datetime, timezone
from uuid import uuid4

import boto3

from app.core.config import get_settings
from app.schemas.site import SiteScreenshotMetadata

logger = logging.getLogger(__name__)

_VIEWPORT_WIDTH = 1440
_VIEWPORT_HEIGHT = 900
_MOBILE_VIEWPORT = {"width": 390, "height": 844}


def capture_site_screenshot(
    site_id: str,
    preview_url: str,
    preview_base_url: str,  # kept for signature compatibility; unused here
) -> SiteScreenshotMetadata | None:
    """
    Navigate to *preview_url*, take a 1440x900 JPEG screenshot and upload
    it to S3.  Returns SiteScreenshotMetadata on success, None on any error.

    This function is synchronous (Playwright sync API) and is intended to be
    called from a thread-pool executor inside an async Celery runner so that
    it never blocks the event loop.
    """
    settings = get_settings()

    bucket = settings.asset_s3_bucket
    if not bucket:
        logger.warning(
            "capture_site_screenshot: ASSET_S3_BUCKET not configured — skipping screenshot for site %s",
            site_id,
        )
        return None

    try:
        sync_playwright = importlib.import_module("playwright.sync_api").sync_playwright
    except Exception:
        logger.warning(
            "capture_site_screenshot: Playwright not available — skipping screenshot for site %s",
            site_id,
        )
        return None

    # ── Take screenshot via Playwright ──────────────────────────────────────
    jpeg_bytes: bytes | None = None
    mobile_bytes: bytes | None = None
    qa: dict[str, object] = {"consoleErrors": [], "pageErrors": [], "failedRequests": [], "assetFailures": [], "hiddenAfterScroll": 0, "mobileMenu": "not-tested"}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            try:
                context = browser.new_context(
                    viewport={"width": _VIEWPORT_WIDTH, "height": _VIEWPORT_HEIGHT}
                )
                page = context.new_page()
                page_errors = qa["pageErrors"]
                page.on("console", lambda msg: qa["consoleErrors"].append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                page.on("requestfailed", lambda req: qa["failedRequests"].append(req.url))
                def inspect_response(response):
                    resource = response.request.resource_type
                    if resource not in {"script", "stylesheet"}:
                        return
                    content_type = response.headers.get("content-type", "").lower()
                    valid_type = (resource == "script" and ("javascript" in content_type or "ecmascript" in content_type)) or (resource == "stylesheet" and "text/css" in content_type)
                    if response.status >= 400 or not valid_type:
                        qa["assetFailures"].append({"url": response.url, "status": response.status, "contentType": content_type, "resource": resource})
                page.on("response", inspect_response)
                page.goto(preview_url, wait_until="networkidle", timeout=30_000)
                frame = page.locator("iframe").first
                if frame.count() > 0:
                    src = frame.get_attribute("src")
                    if src:
                        page.goto(urljoin(preview_url, src), wait_until="networkidle", timeout=30_000)
                page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
                try:
                    page.wait_for_function("Array.from(document.images).every((img) => img.complete)", timeout=15_000)
                except Exception:
                    # Broken images must be reported in QA, not prevent the
                    # screenshot and the rest of the runtime checks.
                    qa["imageLoadTimeout"] = True
                qa["brokenImages"] = page.locator("img").evaluate_all("els => els.filter(img => !img.complete || !img.naturalWidth).length")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(500)
                qa["horizontalOverflow"] = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                qa["fontsReady"] = page.evaluate("document.fonts ? document.fonts.status === 'loaded' : true")
                qa["hiddenAfterScroll"] = page.locator("[data-animate], .animate-on-scroll").evaluate_all("els => els.filter(el => getComputedStyle(el).opacity === '0' || getComputedStyle(el).visibility === 'hidden').length")
                runtime = page.evaluate("""() => ({ ready: window.__LENMANAG_STATIC_READY__ === true, runtime: window.__LENMANAG_RUNTIME__ || null, mainVisible: !!document.querySelector('main') && document.querySelector('main').getBoundingClientRect().height > 0 })""")
                qa["readiness"] = runtime.get("ready")
                qa["runtimeInitializationError"] = (runtime.get("runtime") or {}).get("errors") or []
                qa["mainContentRendered"] = runtime.get("mainVisible")
                jpeg_bytes = page.screenshot(full_page=True, type="jpeg", quality=85)
                mobile_context = browser.new_context(viewport=_MOBILE_VIEWPORT)
                mobile = mobile_context.new_page()
                mobile.goto(page.url, wait_until="networkidle", timeout=30_000)
                mobile.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
                try:
                    mobile.wait_for_function("Array.from(document.images).every((img) => img.complete)", timeout=15_000)
                except Exception:
                    qa["mobileImageLoadTimeout"] = True
                menu = mobile.locator("button[aria-label*='menu' i], button:has-text('Menu'), [data-menu-toggle]").first
                if menu.count() > 0:
                    menu.click()
                    opened = mobile.locator("nav:visible, [role='menu']:visible, .mobile-menu:visible").count() > 0
                    menu.click()
                    closed = mobile.locator("nav:visible, [role='menu']:visible, .mobile-menu:visible").count() == 0
                    qa["mobileMenu"] = "passed" if opened and closed else "failed"
                mobile_bytes = mobile.screenshot(full_page=True, type="jpeg", quality=85)
                mobile.close()
                mobile_context.close()
            finally:
                browser.close()
    except Exception as exc:
        logger.error(
            "capture_site_screenshot: Playwright failed for site %s: %s",
            site_id,
            exc,
            exc_info=True,
        )
        return None

    if not jpeg_bytes:
        logger.error(
            "capture_site_screenshot: empty screenshot bytes for site %s",
            site_id,
        )
        return None

    # ── Upload to S3 ─────────────────────────────────────────────────────────
    prefix = settings.asset_s3_prefix or "lenmanag/"
    s3_key = f"{prefix}screenshots/{site_id}/preview.jpg"

    try:
        s3_client = boto3.client(
            "s3",
            region_name=settings.asset_s3_region or "us-east-1",
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=jpeg_bytes,
            ContentType="image/jpeg",
            CacheControl="public, max-age=86400",
        )
        if mobile_bytes:
            s3_client.put_object(Bucket=bucket, Key=f"{prefix}screenshots/{site_id}/mobile.jpg", Body=mobile_bytes, ContentType="image/jpeg", CacheControl="public, max-age=86400")
    except Exception as exc:
        logger.error(
            "capture_site_screenshot: S3 upload failed for site %s: %s",
            site_id,
            exc,
            exc_info=True,
        )
        return None

    backend_public_url = os.getenv(
        "BACKEND_PUBLIC_URL", "http://localhost:8000"
    ).rstrip("/")
    screenshot_url = f"{backend_public_url}/api/v1/screenshots/{site_id}/preview.jpg"

    qa["fatalRuntimeFailures"] = _fatal_runtime_failures(qa)
    qa["runtimeStatus"] = "failed" if qa["fatalRuntimeFailures"] else "passed"
    return SiteScreenshotMetadata(
        id=uuid4().hex,
        label="preview",
        url=screenshot_url,
        capturedAt=datetime.now(timezone.utc),
        width=_VIEWPORT_WIDTH,
        height=_VIEWPORT_HEIGHT,
        notes=json.dumps({**qa, "mobileUrl": f"{backend_public_url}/api/v1/screenshots/{site_id}/mobile.jpg" if mobile_bytes else None}),
    )


def _fatal_runtime_failures(qa: dict[str, object]) -> list[str]:
    """Deterministic health gate; vision scoring is deliberately irrelevant."""
    failures: list[str] = []
    if qa.get("consoleErrors"): failures.append("console_errors")
    if qa.get("pageErrors"): failures.append("page_errors")
    if qa.get("failedRequests"): failures.append("failed_requests")
    if qa.get("assetFailures"): failures.append("generated_asset_request_or_mime")
    if qa.get("readiness") is not True: failures.append("readiness_missing_or_false")
    if qa.get("runtimeInitializationError"): failures.append("runtime_initialization_error")
    if qa.get("mainContentRendered") is not True: failures.append("main_content_not_rendered")
    if qa.get("mobileMenu") == "failed": failures.append("mobile_menu_failed")
    if qa.get("hiddenAfterScroll"): failures.append("content_hidden_after_scroll")
    if qa.get("horizontalOverflow"): failures.append("horizontal_overflow")
    return failures
