from __future__ import annotations

from typing import cast

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
    Looks up the lead by redesignSlug and returns all variants that have
    been successfully compiled and have at least one screenshot.
    """
    database = get_database()
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    lead_doc = await database["leads"].find_one({"redesignSlug": slug})
    if lead_doc is None:
        raise HTTPException(status_code=404, detail="Redesign page not found")

    lead_id: str = str(lead_doc["id"])

    # Fetch all sites for this lead
    sites = await site_repository.list_sites_by_lead(lead_id)

    # Galleries can include any generated site; screenshots remain optional.
    eligible = list(sites)

    # Missing/null settings preserve the default of showing every site.
    # An explicit list controls both gallery membership and display order.
    selected_site_ids = lead_doc.get("gallerySiteIds")
    if selected_site_ids is not None:
        sites_by_id = {site.id: site for site in eligible}
        eligible = [
            sites_by_id[str(site_id)]
            for site_id in selected_site_ids
            if str(site_id) in sites_by_id
        ]

    if not eligible:
        raise HTTPException(status_code=404, detail="Redesign page not found")

    # For default galleries use the sites' assigned positions. Explicit
    # selections already follow the saved order from the lead document.
    if selected_site_ids is None:
        eligible.sort(key=lambda s: s.variantPosition)

    # Build variant list — use first screenshot if available, else empty string
    variants: list[RedesignVariant] = []
    for site in eligible:
        screenshot_url = site.screenshotRefs[0].url if site.screenshotRefs else ""
        variants.append(
            RedesignVariant(
                siteId=site.id,
                variantLabel=site.variantLabel,
                variantDescription=site.variantDescription,
                previewUrl=site.previewUrl,
                screenshotUrl=screenshot_url,
                variantPosition=site.variantPosition,
            )
        )

    # Try to get logo from master brief
    logo_url: str | None = None
    try:
        master_brief = await lead_repository.get_master_brief(lead_id)
        if master_brief is not None and master_brief.brandAssets.logoUrl:
            logo_url = master_brief.brandAssets.logoUrl
    except Exception:
        pass  # Best effort — logo is optional

    data = RedesignPageData(
        leadId=lead_id,
        companyName=lead_doc.get("companyName"),
        contactName=lead_doc.get("contactName"),
        logoUrl=logo_url,
        callUrl=lead_doc.get("galleryCallUrl") or "https://calendly.com/lenquant/sites",
        variants=variants,
    )

    return cast(
        ResponseEnvelope[RedesignPageData],
        success_response(data, meta=response_meta(request)),
    )
