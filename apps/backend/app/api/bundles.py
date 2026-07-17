"""
Bundle proxy endpoint - serves compiled site bundles with proper CORS headers.
Proxies S3 bundles through the backend to add CORS headers.
"""

from fastapi import APIRouter, HTTPException, Response
import httpx

from app.core.config import get_settings

router = APIRouter(prefix="/bundles", tags=["bundles"])
settings = get_settings()


@router.get("/{site_id}/bundle.js")
async def get_bundle_js(site_id: str) -> Response:
    """
    Proxy bundle.js from S3 with proper CORS headers.
    This allows the frontend to load bundles without CORS issues.
    """
    prefix = settings.asset_s3_prefix or "lenmanag/"
    bucket = settings.asset_s3_bucket
    region = settings.asset_s3_region or "us-east-1"

    bundle_url = f"https://{bucket}.s3.{region}.amazonaws.com/{prefix}bundles/{site_id}/bundle.js"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(bundle_url, timeout=30.0)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=404, detail=f"Bundle not found for site {site_id}"
                )

            return Response(
                content=response.content,
                media_type="application/javascript",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Cache-Control": "public, max-age=3600",
                },
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to fetch bundle from S3: {str(e)}"
            )


@router.get("/{site_id}/styles.css")
async def get_bundle_css(site_id: str) -> Response:
    """
    Proxy styles.css from S3 with proper CORS headers.
    """
    prefix = settings.asset_s3_prefix or "lenmanag/"
    bucket = settings.asset_s3_bucket
    region = settings.asset_s3_region or "us-east-1"

    css_url = f"https://{bucket}.s3.{region}.amazonaws.com/{prefix}bundles/{site_id}/styles.css"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(css_url, timeout=30.0)
            if response.status_code != 200:
                # CSS is optional, return empty stylesheet
                return Response(
                    content="",
                    media_type="text/css",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=3600",
                    },
                )

            return Response(
                content=response.content,
                media_type="text/css",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Cache-Control": "public, max-age=3600",
                },
            )
        except httpx.RequestError:
            # CSS is optional, return empty stylesheet
            return Response(
                content="",
                media_type="text/css",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=3600",
                },
            )
