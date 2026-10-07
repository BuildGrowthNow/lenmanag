from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import cast
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.config import get_settings
from app.core.leads import lead_repository
from app.core.sites import (
    CLIENT_VARIANT_COPY,
    has_renderable_generated_artifact,
    is_artifact_generated_site,
    is_usable_generated_site,
)
from app.core.mongo import get_database
from app.core.rate_limiter import check_public_form_rate_limit
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
    return is_usable_generated_site(site)


def _all_public_variants(sites: list[GeneratedSite]) -> list[GeneratedSite]:
    """Return every usable built variant; the operator may optionally narrow it."""
    return sorted(
        (site for site in sites if _publicly_eligible(site)),
        key=lambda site: (site.variantPosition, site.createdAt, site.id),
    )


def _selected_share_variant(site: GeneratedSite) -> bool:
    """Keep an existing client selection live after a QA warning.

    A warning is not the same as a blocked or missing artifact. Previously
    shared links must continue to show their selected, successfully built
    variants even when a later QA pass records a warning instead of a pass.
    New galleries still use the stricter ``_publicly_eligible`` filter.
    """
    return is_artifact_generated_site(site)


def _client_variant_copy(site: GeneratedSite) -> tuple[str, str]:
    default_title, default_description = CLIENT_VARIANT_COPY.get(
        str(site.variantType), ("A New Direction", "A distinct visual direction shaped around the approved brief.")
    )
    return site.variantTitle or default_title, site.variantDescription or default_description


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
    # Operator previews can inspect a complete artifact while QA is blocked;
    # publication, shares, and forms still require the stricter readiness gate.
    if not has_renderable_generated_artifact(site):
        raise HTTPException(status_code=409, detail="Site preview is not available yet")

    if site.variantType in ["html_v1", "html_v2", "html_v3"]:
        return HTMLResponse(
            content=site.staticHtml or "",
            headers={
                "Cache-Control": "no-store",
                "X-LenManag-Preview-Type": "static-html",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            },
        )

    settings = get_settings()
    preview_base = settings.preview_base_url.rstrip("/")
    return RedirectResponse(url=f"{preview_base}/{site.previewSlug}")


@router.post("/forms/{site_id}", response_class=HTMLResponse, status_code=200)
async def submit_public_form(site_id: str, request: Request) -> HTMLResponse:
    """Persist a generated-site contact form submission.

    Generated static pages use native POST forms so delivery still works when
    JavaScript is disabled and generated runtimes never need network access.
    """
    check_public_form_rate_limit(request, f"public-form:{site_id}")
    _check_public_form_origin(request)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 16_384:
                raise HTTPException(status_code=413, detail="Form payload is too large")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid content length") from exc
    site = await site_repository.get_site(site_id)
    if site is None or not is_artifact_generated_site(site):
        raise HTTPException(status_code=404, detail="Site form is unavailable")

    body = await request.body()
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid form payload") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid form payload")
    else:
        payload = {
            key: values[-1]
            for key, values in parse_qs(
                body.decode("utf-8"), keep_blank_values=True
            ).items()
        }

    # Honeypot submissions are acknowledged without persistence.
    if str(payload.get("website", "")).strip():
        return HTMLResponse(_form_confirmation_page())

    def clean(name: str, limit: int) -> str:
        return str(payload.get(name, "") or "").strip()[:limit]

    name = clean("name", 160)
    email = clean("email", 320).lower()
    message = clean("message", 4000)
    phone = clean("phone", 80)
    company = clean("company", 160)
    if not email or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="A valid email is required")
    if not name and not message:
        raise HTTPException(status_code=422, detail="Name or message is required")

    database = get_database()
    if database is None:
        raise HTTPException(status_code=503, detail="Form delivery is unavailable")
    notification_target = get_settings().public_form_notification_email.strip().lower()
    submission = {
            "siteId": site_id,
            "leadId": site.leadId,
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "message": message,
            "source": "generated_site_form",
            "createdAt": datetime.now(timezone.utc),
            "deliveryStatus": "stored_only",
        }
    result = await database["public_form_submissions"].insert_one(submission)
    notified = False
    if notification_target:
        from app.core.email_service import send_public_form_notification

        notified = await send_public_form_notification(
            recipient=notification_target,
            submission_id=str(result.inserted_id),
            site_id=site_id,
            name=name,
            email=email,
            message=message,
            phone=phone,
            company=company,
        )
        await database["public_form_submissions"].update_one(
            {"_id": result.inserted_id},
            {"$set": {"deliveryStatus": "notified" if notified else "notification_failed", "notifiedAt": datetime.now(timezone.utc) if notified else None}},
        )
    return HTMLResponse(_form_confirmation_page())


def _check_public_form_origin(request: Request) -> None:
    """Reject browser submissions from unrelated origins when a browser sends one."""
    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    referer = (request.headers.get("referer") or "").strip()
    candidate = origin or (urlparse(referer).scheme + "://" + urlparse(referer).netloc if referer else "")
    if not candidate:
        return
    settings = get_settings()
    allowed = {
        urlparse(settings.frontend_url).scheme + "://" + urlparse(settings.frontend_url).netloc,
        urlparse(settings.backend_public_url).scheme + "://" + urlparse(settings.backend_public_url).netloc,
        urlparse(settings.preview_base_url).scheme + "://" + urlparse(settings.preview_base_url).netloc,
    }
    if candidate not in {value.rstrip("/") for value in allowed if value != "://"}:
        raise HTTPException(status_code=403, detail="Form origin is not allowed")


def _form_confirmation_page() -> str:
    return """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Message received</title></head><body><main><h1>Message received</h1><p>Thanks. The team will be in touch soon.</p></main></body></html>"""


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

    # Older client links were saved only under clientShare.slug when the lead
    # did not yet have a redesignSlug. Resolve both representations so links
    # already sent to clients remain valid after the schema was extended.
    normalized_slug = _normalize_preview_slug(slug)
    lead_doc = await database["leads"].find_one(
        {
            "$or": [
                {"redesignSlug": normalized_slug},
                {"clientShare.slug": normalized_slug},
            ]
        }
    )
    if lead_doc is None:
        raise HTTPException(status_code=404, detail="Redesign page not found")

    lead_id: str = str(lead_doc["id"])

    sites = await site_repository.list_sites_by_lead(lead_id)
    all_eligible = _all_public_variants(sites)
    share = lead_doc.get("clientShare") or {}
    selected_ids = list(share.get("selectedSiteIds") or [])
    if selected_ids:
        by_id = {site.id: site for site in sites if _selected_share_variant(site)}
        eligible = [by_id[site_id] for site_id in selected_ids if site_id in by_id]
        # A client link must remain useful when an operator removes or
        # invalidates one of the variants that was selected earlier. Keep the
        # saved order for still-available variants and fall back to every
        # current usable variant if the saved selection is fully stale.
        if not eligible:
            eligible = all_eligible
    else:
        eligible = all_eligible

    if not eligible:
        raise HTTPException(status_code=404, detail="Redesign page not found")

    # Preserve the saved selection order. Screenshots are optional.
    variants: list[RedesignVariant] = []
    for option_number, site in enumerate(eligible, start=1):
        variant_title, variant_description = _client_variant_copy(site)
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
                variantTitle=variant_title,
                variantDescription=variant_description,
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
        bookingUrl=share.get("bookingUrl") or "https://calendly.com/lenquant/sites",
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
