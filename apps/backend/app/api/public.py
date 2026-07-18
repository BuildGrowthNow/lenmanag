from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.config import get_settings
from app.core.sites import site_repository
from app.core.versioning import response_meta
from app.schemas.response import ResponseEnvelope, success_response
from app.schemas.site import GeneratedSite

router = APIRouter(prefix="/public", tags=["public"])


def _normalize_preview_slug(slug: str) -> str:
    return slug.strip().rstrip("`'\" ")


@router.get("/st/{slug}", response_model=ResponseEnvelope[GeneratedSite])
async def get_public_site(
    slug: str, request: Request
) -> ResponseEnvelope[GeneratedSite]:
    site = await site_repository.get_site_by_slug(_normalize_preview_slug(slug))
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return cast(
        ResponseEnvelope[GeneratedSite],
        success_response(site, meta=response_meta(request)),
    )


@router.get("/preview/{slug}", response_class=Response)
async def preview_site_variant(slug: str) -> Response:
    """
    Public preview of a site variant (HTML or Next.js).

    For static HTML variants: returns HTML with linked CSS/JS
    For Next.js variants: redirects to Next.js preview
    """
    site = await site_repository.get_site_by_slug(_normalize_preview_slug(slug))
    if site is None:
        raise HTTPException(status_code=404, detail="Site preview not found")

    if site.variantType in ["html_v1", "html_v2", "html_v3"]:
        if not site.staticHtml:
            raise HTTPException(status_code=500, detail="Static HTML not generated")

        return HTMLResponse(content=site.staticHtml)

    settings = get_settings()
    preview_base = settings.preview_base_url.rstrip("/")
    return RedirectResponse(url=f"{preview_base}/{site.previewSlug}")
