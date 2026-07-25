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
from datetime import datetime, timezone
from uuid import uuid4

import boto3

from app.core.config import get_settings
from app.schemas.site import SiteScreenshotMetadata

logger = logging.getLogger(__name__)

_VIEWPORT_WIDTH = 1440
_VIEWPORT_HEIGHT = 900


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
                page.goto(preview_url, wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(2_000)
                jpeg_bytes = page.screenshot(full_page=False, type="jpeg", quality=85)
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

    return SiteScreenshotMetadata(
        id=uuid4().hex,
        label="preview",
        url=screenshot_url,
        capturedAt=datetime.now(timezone.utc),
        width=_VIEWPORT_WIDTH,
        height=_VIEWPORT_HEIGHT,
    )
