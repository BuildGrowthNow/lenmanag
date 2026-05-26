from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException

from app.core.audit import write_audit_log
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.core.sites import site_repository
from app.schemas.site import (
    GeneratedSite,
    GeneratedSiteVersionResponse,
    SiteCompareResponse,
    SiteExportMetadata,
    SiteExportRequest,
    SiteGenerateRequest,
    SiteHandoffRecord,
    SiteReviewPatchRequest,
    SiteReviewQueueResponse,
    SiteReviewRecord,
    SiteReviewRequest,
    SiteOverrideCreateRequest,
    SiteOverrideRecord,
    SiteReviewResponse,
    ThemeLibraryResponse,
)

router = APIRouter(prefix="/sites", tags=["sites"])
themes_router = APIRouter(tags=["sites"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@themes_router.get("/themes", response_model=ThemeLibraryResponse)
async def list_themes(session: dict = Depends(_require_session)) -> ThemeLibraryResponse:
    return site_repository.get_theme_library()


@router.get("/{site_id}", response_model=GeneratedSite | None)
async def get_site(site_id: str, session: dict = Depends(_require_session)) -> GeneratedSite | None:
    return await site_repository.get_site(site_id)


@router.get("/{site_id}/versions", response_model=GeneratedSiteVersionResponse | None)
async def get_versions(site_id: str, session: dict = Depends(_require_session)) -> GeneratedSiteVersionResponse | None:
    return await site_repository.list_versions(site_id)


@router.get("/{site_id}/compare", response_model=SiteCompareResponse | None)
async def get_compare(site_id: str, session: dict = Depends(_require_session)) -> SiteCompareResponse | None:
    return await site_repository.get_compare(site_id)


@router.get("/review-queue", response_model=SiteReviewQueueResponse)
async def review_queue(limit: int = 25, offset: int = 0, session: dict = Depends(_require_session)) -> SiteReviewQueueResponse:
    return await site_repository.list_review_queue(limit=limit, offset=offset)


@router.get("/{site_id}/review", response_model=SiteReviewResponse)
async def get_review(site_id: str, session: dict = Depends(_require_session)) -> SiteReviewResponse:
    return SiteReviewResponse(review=await site_repository.get_review(site_id))


@router.post("/{site_id}/review", response_model=SiteReviewRecord)
async def add_review(site_id: str, request: SiteReviewRequest, session: dict = Depends(_require_session)) -> SiteReviewRecord:
    review = await site_repository.upsert_review(site_id, request, actor=session["email"])
    if review is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(session["email"], "site", site_id, "site_review_create", after=review.model_dump())
    return review


@router.patch("/{site_id}/review", response_model=SiteReviewRecord)
async def patch_review(site_id: str, request: SiteReviewPatchRequest, session: dict = Depends(_require_session)) -> SiteReviewRecord:
    review = await site_repository.upsert_review(site_id, request, actor=session["email"])
    if review is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(session["email"], "site", site_id, "site_review_update", after=review.model_dump())
    return review


@router.post("/{site_id}/review/approve", response_model=SiteHandoffRecord)
async def approve_review(site_id: str, session: dict = Depends(_require_session)) -> SiteHandoffRecord:
    handoff = await site_repository.publish_handoff(site_id)
    if handoff is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(session["email"], "site", site_id, "site_review_approve", after=handoff.model_dump())
    return handoff


@router.get("/{site_id}/handoff", response_model=SiteHandoffRecord)
async def get_handoff(site_id: str, session: dict = Depends(_require_session)) -> SiteHandoffRecord:
    handoff = await site_repository.get_handoff(site_id)
    if handoff is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return handoff


@router.post("/{site_id}/regenerate", response_model=GeneratedSite)
async def regenerate_site(site_id: str, session: dict = Depends(_require_session)) -> GeneratedSite:
    site = await site_repository.retry_generation(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(session["email"], "site", site_id, "site_regenerate", after=site.model_dump())
    return site


@router.post("/{site_id}/generate", response_model=GeneratedSite)
async def generate_site(
    site_id: str,
    request: SiteGenerateRequest | None = None,
    session: dict = Depends(_require_session),
) -> GeneratedSite:
    try:
        site = await site_repository.generate_site(site_id, request=request)
    except ValueError as exc:
        if str(exc) == "brief_not_approved":
            raise HTTPException(status_code=409, detail="Approve the site brief before generating a preview.") from exc
        if str(exc) == "extraction_required":
            raise HTTPException(status_code=409, detail="Create a site extraction before generating a preview.") from exc
        raise
    if site is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "site", site_id, "site_generate", after=site.model_dump())
    return site


@router.post("/{site_id}/republish", response_model=GeneratedSite)
async def republish_site(site_id: str, session: dict = Depends(_require_session)) -> GeneratedSite:
    try:
        site = await site_repository.republish_site(site_id)
    except ValueError as exc:
        if str(exc) == "brief_not_approved":
            raise HTTPException(status_code=409, detail="Approve the site brief before republishing a preview.") from exc
        if str(exc) == "extraction_required":
            raise HTTPException(status_code=409, detail="Create a site extraction before republishing a preview.") from exc
        raise
    if site is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "site", site_id, "site_republish", after=site.model_dump())
    return site


@router.post("/{site_id}/overrides", response_model=SiteOverrideRecord)
async def add_override(
    site_id: str,
    request: SiteOverrideCreateRequest,
    session: dict = Depends(_require_session),
) -> SiteOverrideRecord:
    record = await site_repository.create_override(site_id, request, actor=session["email"])
    if record is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(session["email"], "site", site_id, "site_override_create", after=record.model_dump())
    return record


@router.post("/{site_id}/export", response_model=SiteExportMetadata)
async def export_site(
    site_id: str,
    request: SiteExportRequest,
    session: dict = Depends(_require_session),
) -> SiteExportMetadata:
    now = datetime.now(timezone.utc)
    metadata = SiteExportMetadata(
        exportType=request.exportType,
        repoUrl=request.repoUrl,
        branch=request.branch,
        commitSha=request.commitSha,
        exportPath=request.exportPath,
        notes=request.notes,
        createdAt=now,
        updatedAt=now,
    )
    export_metadata = await site_repository.add_export_metadata(site_id, metadata)
    if export_metadata is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(session["email"], "site", site_id, "site_export_create", after=export_metadata.model_dump())
    return export_metadata


@router.get("/{site_id}/export", response_model=SiteExportMetadata | None)
async def get_export(site_id: str, session: dict = Depends(_require_session)) -> SiteExportMetadata | None:
    site = await site_repository.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return site.exportMetadata
