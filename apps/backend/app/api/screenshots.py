"""
Public screenshot proxy — serves site preview JPEG screenshots from S3.
No authentication required: these are public assets linked from client-facing pages.
"""

from __future__ import annotations

import logging

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.config import get_settings

router = APIRouter(prefix="/screenshots", tags=["screenshots"])
logger = logging.getLogger(__name__)


@router.get("/{site_id}/preview.jpg")
async def get_site_screenshot(site_id: str) -> Response:
    """
    Fetch a site's preview JPEG from S3 and return it with cache headers.
    Returns 404 if the screenshot has not been captured yet.
    """
    settings = get_settings()
    bucket = settings.asset_s3_bucket
    if not bucket:
        raise HTTPException(status_code=404, detail="Screenshots not available")

    prefix = settings.asset_s3_prefix or "lenmanag/"
    s3_key = f"{prefix}screenshots/{site_id}/preview.jpg"

    try:
        s3_client = boto3.client(
            "s3",
            region_name=settings.asset_s3_region or "us-east-1",
        )
        obj = s3_client.get_object(Bucket=bucket, Key=s3_key)
        jpeg_bytes: bytes = obj["Body"].read()
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("NoSuchKey", "404"):
            raise HTTPException(status_code=404, detail="Screenshot not found") from exc
        logger.error(
            "get_site_screenshot: S3 error for site %s key %s: %s",
            site_id,
            s3_key,
            exc,
        )
        raise HTTPException(
            status_code=502, detail="Failed to fetch screenshot"
        ) from exc

    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
