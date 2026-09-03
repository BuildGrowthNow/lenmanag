"""Public proxy for generated CSS and JavaScript bundles.

Bundles remain private in object storage while previews receive stable
LenQuant-hosted URLs. This also gives CSP and cache policy one controlled edge.
"""

from __future__ import annotations

import logging
import re

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.config import get_settings

router = APIRouter(prefix="/static-assets", tags=["static-assets"])
logger = logging.getLogger(__name__)


@router.get("/{site_id}/{asset_type}")
async def get_static_asset(
    site_id: str, asset_type: str, version: str | None = Query(default=None, alias="v")
) -> Response:
    """Serve an approved generated bundle without exposing storage URLs."""
    content_type = {
        "css": "text/css; charset=utf-8",
        "js": "application/javascript; charset=utf-8",
    }.get(asset_type)
    if not content_type:
        raise HTTPException(status_code=404, detail="Generated asset not found")
    settings = get_settings()
    if not settings.asset_s3_bucket:
        raise HTTPException(status_code=404, detail="Generated assets unavailable")
    prefix = settings.asset_s3_prefix or "lenmanag/"
    extension = "styles.css" if asset_type == "css" else "script.js"
    if version is not None and not re.fullmatch(r"[a-f0-9]{16}", version):
        raise HTTPException(status_code=404, detail="Generated asset not found")
    version_path = f"/{version}" if version else ""
    key = f"{prefix}static-sites/{site_id}{version_path}/{extension}"
    try:
        client = boto3.client("s3", region_name=settings.asset_s3_region or "us-east-1")
        body = client.get_object(Bucket=settings.asset_s3_bucket, Key=key)[
            "Body"
        ].read()
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"NoSuchKey", "404"}:
            raise HTTPException(
                status_code=404, detail="Generated asset not found"
            ) from exc
        logger.error(
            "Generated asset fetch failed for %s/%s: %s", site_id, asset_type, exc
        )
        raise HTTPException(
            status_code=502, detail="Failed to fetch generated asset"
        ) from exc
    return Response(
        content=body,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
