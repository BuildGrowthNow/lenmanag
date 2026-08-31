from __future__ import annotations

from typing import cast
import os
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.config import get_settings
from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.core.sites import site_repository
from app.core.versioning import response_meta
from app.schemas.response import ResponseEnvelope, success_response
from app.schemas.site import GeneratedSite, RedesignPageData, RedesignVariant

router = APIRouter(prefix="/public", tags=["public"])


def _normalize_preview_slug(slug: str) -> str:
    return slug.strip().rstrip("`'\" ")


def _public_image_url(value: object) -> str | None:
    """Return an image URL only when it looks like an actual image asset."""
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    path = parsed.path.lower().split("?")[0]
    if not path.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".avif")):
        return None
    return value.strip()


def _publicly_eligible(site: GeneratedSite) -> bool:
    return (
        site.readinessStatus != "blocked"
        and bool(site.previewUrl or site.previewSlug)
        and (site.compilationStatus in {"success", "completed"} or bool(site.staticHtml))
    )


def _all_public_variants(sites: list[GeneratedSite]) -> list[GeneratedSite]:
    """Return every usable built variant; the operator may optionally narrow it."""
    return sorted(
        (site for site in sites if _publicly_eligible(site)),
        key=lambda site: (site.variantPosition, site.createdAt, site.id),
    )


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


@router.get("/redesign/{slug}", response_model=ResponseEnvelope[RedesignPageData])
async def get_redesign_page(
    slug: str, request: Request
) -> ResponseEnvelope[RedesignPageData]:
    """
    Public client-facing endpoint: returns data for the /redesign/{slug} page.
    Looks up the lead by redesignSlug. The public payload is intentionally small
    and exposes all current, usable strategy variants without full site records.
    """
    database = get_database()
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    lead_doc = await database["leads"].find_one({"redesignSlug": slug})
    if lead_doc is None:
        raise HTTPException(status_code=404, detail="Redesign page not found")

    lead_id: str = str(lead_doc["id"])

    sites = await site_repository.list_sites_by_lead(lead_id)
    all_eligible = _all_public_variants(sites)
    share = lead_doc.get("clientShare") or {}
    selected_ids = list(share.get("selectedSiteIds") or [])
    if selected_ids:
        by_id = {site.id: site for site in all_eligible}
        eligible = [by_id[site_id] for site_id in selected_ids if site_id in by_id]
        if len(eligible) != len(selected_ids):
            raise HTTPException(status_code=404, detail="Redesign page not found")
    else:
        eligible = all_eligible

    if not eligible:
        raise HTTPException(status_code=404, detail="Redesign page not found")

    # Preserve the saved selection order. Screenshots are optional.
    variants: list[RedesignVariant] = []
    for option_number, site in enumerate(eligible, start=1):
        screenshot_url = site.screenshotRefs[0].url if site.screenshotRefs else ""
        preview_url = site.previewUrl
        if not preview_url or "localhost" in preview_url or "127.0.0.1" in preview_url:
            preview_url = f"{os.getenv('FRONTEND_PUBLIC_URL', 'https://sites.lenquant.com').rstrip('/')}/st/{site.previewSlug}"
        variants.append(
            RedesignVariant(
                siteId=site.id,
                previewUrl=preview_url,
                screenshotUrl=screenshot_url,
                variantPosition=site.variantPosition,
                optionNumber=option_number,
                variantLabel=site.variantLabel,
            )
        )

    # Try to get logo from master brief
    logo_url: str | None = None
    try:
        master_brief = await lead_repository.get_master_brief(lead_id)
        if master_brief is not None:
            logo_url = _public_image_url(master_brief.brandAssets.logoUrl)
    except Exception:
        pass  # Best effort — logo is optional

    data = RedesignPageData(
        leadId=lead_id,
        companyName=lead_doc.get("companyName"),
        contactName=lead_doc.get("contactName"),
        logoUrl=logo_url,
        variants=variants,
    )

    return cast(
        ResponseEnvelope[RedesignPageData],
        success_response(data, meta=response_meta(request)),
    )


@router.get("/compare/{lead_id}", response_model=ResponseEnvelope[RedesignPageData])
async def get_public_compare(
    lead_id: str, request: Request
) -> ResponseEnvelope[RedesignPageData]:
    """Compatibility endpoint for the operator preview, backed by the saved share."""
    database = get_database()
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    lead_doc = await database["leads"].find_one({"id": lead_id})
    slug = lead_doc.get("redesignSlug") if lead_doc else None
    if not slug:
        raise HTTPException(status_code=404, detail="Compare page not found")
    return await get_redesign_page(slug, request)
