from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, cast

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.audit import write_audit_log
from app.core.leads import lead_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.core.sites import site_repository, validate_operator_prompt
from app.core.versioning import response_meta
from app.schemas.job import JobResponse
from app.schemas.response import ResponseEnvelope, success_response
from app.schemas.site import (
    GeneratedSite,
    GeneratedSiteVersionResponse,
    RefinementPromptRecord,
    SiteCompareResponse,
    SiteExportMetadata,
    SiteExportRecord,
    SiteExportRequest,
    SiteGenerateRequest,
    SiteHandoffRecord,
    SiteOverrideCreateRequest,
    SiteOverrideRecord,
    SiteReviewPatchRequest,
    SiteReviewQueueResponse,
    SiteReviewRecord,
    SiteReviewRequest,
    SiteReviewResponse,
    ThemeLibraryResponse,
)

router = APIRouter(prefix="/sites", tags=["sites"])
themes_router = APIRouter(tags=["sites"])


async def _require_session(
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


async def _job_response(job) -> JobResponse:
    job_doc = await lead_repository.get_job_doc(job.id)
    lead_ids_raw = list(job_doc.get("leadIds", [])) if job_doc else []
    lead_ids = [str(lid) for lid in lead_ids_raw if lid is not None]
    metadata = dict(job_doc.get("metadata", {})) if job_doc else {}
    if not lead_ids:
        lead_id = job_doc.get("leadId") if job_doc else None
        lead_ids = [str(lead_id)] if lead_id else []
    return JobResponse(job=job, leadIds=lead_ids, metadata=metadata)


@themes_router.get("/themes", response_model=ResponseEnvelope[ThemeLibraryResponse])
async def list_themes(
    request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[ThemeLibraryResponse]:
    return success_response(
        site_repository.get_theme_library(), meta=response_meta(request)
    )


@router.get("", response_model=ResponseEnvelope[list[GeneratedSite]])
async def list_sites(
    request: Request,
    limit: int = 25,
    offset: int = 0,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[list[GeneratedSite]]:
    return cast(
        ResponseEnvelope[list[GeneratedSite]],
        success_response(
            await site_repository.list_sites(limit=limit, offset=offset),
            meta=response_meta(request),
        ),
    )


@router.get("/review-queue", response_model=ResponseEnvelope[SiteReviewQueueResponse])
async def review_queue(
    request: Request,
    limit: int = 25,
    offset: int = 0,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteReviewQueueResponse]:
    return success_response(
        await site_repository.list_review_queue(limit=limit, offset=offset),
        meta=response_meta(request),
    )


@router.get("/diversity-report", response_model=ResponseEnvelope[dict[str, Any]])
async def diversity_report(
    request: Request,
    limit: int = 100,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[dict[str, Any]]:
    return success_response(
        await site_repository.get_diversity_report(limit=limit),
        meta=response_meta(request),
    )


@router.get("/{site_id}", response_model=ResponseEnvelope[GeneratedSite | None])
async def get_site(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[GeneratedSite | None]:
    site = await site_repository.get_site(site_id)
    return success_response(site, meta=response_meta(request))


@router.get(
    "/{site_id}/prompts",
    response_model=ResponseEnvelope[list[RefinementPromptRecord]],
)
async def get_prompt_history(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[list[RefinementPromptRecord]]:
    history = await site_repository.get_prompt_history(site_id)
    return success_response(history, meta=response_meta(request))


@router.get(
    "/{site_id}/versions",
    response_model=ResponseEnvelope[GeneratedSiteVersionResponse | None],
)
async def get_versions(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[GeneratedSiteVersionResponse | None]:
    return success_response(
        await site_repository.list_versions(site_id), meta=response_meta(request)
    )


@router.get(
    "/{site_id}/compare", response_model=ResponseEnvelope[SiteCompareResponse | None]
)
async def get_compare(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[SiteCompareResponse | None]:
    return success_response(
        await site_repository.get_compare(site_id), meta=response_meta(request)
    )


@router.get("/{site_id}/review", response_model=ResponseEnvelope[SiteReviewResponse])
async def get_review(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[SiteReviewResponse]:
    return success_response(
        SiteReviewResponse(review=await site_repository.get_review(site_id)),
        meta=response_meta(request),
    )


@router.post("/{site_id}/review", response_model=ResponseEnvelope[SiteReviewRecord])
async def add_review(
    site_id: str,
    payload: SiteReviewRequest,
    request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteReviewRecord]:
    review = await site_repository.upsert_review(
        site_id, payload, actor=session["email"]
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_review_create",
        after=review.model_dump(),
    )
    return success_response(review, meta=response_meta(request))


@router.patch("/{site_id}/review", response_model=ResponseEnvelope[SiteReviewRecord])
async def patch_review(
    site_id: str,
    payload: SiteReviewPatchRequest,
    request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteReviewRecord]:
    review = await site_repository.upsert_review(
        site_id, payload, actor=session["email"]
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_review_update",
        after=review.model_dump(),
    )
    return success_response(review, meta=response_meta(request))


@router.post(
    "/{site_id}/review/approve", response_model=ResponseEnvelope[SiteHandoffRecord]
)
async def approve_review(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[SiteHandoffRecord]:
    handoff = await site_repository.publish_handoff(site_id)
    if handoff is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_review_approve",
        after=handoff.model_dump(),
    )
    return success_response(handoff, meta=response_meta(request))


@router.get("/{site_id}/handoff", response_model=ResponseEnvelope[SiteHandoffRecord])
async def get_handoff(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[SiteHandoffRecord]:
    handoff = await site_repository.get_handoff(site_id)
    if handoff is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return success_response(handoff, meta=response_meta(request))


@router.post(
    "/{site_id}/regenerate",
    response_model=ResponseEnvelope[JobResponse],
    status_code=202,
)
async def regenerate_site_with_prompt(
    site_id: str,
    payload: dict[str, Any],
    request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[JobResponse]:
    refinement_prompt = (payload.get("refinementPrompt") or "").strip()
    force = bool(payload.get("force", False))

    is_valid, error_message = validate_operator_prompt(refinement_prompt)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    site = await site_repository.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")

    if not force and (site.qualityScore or 0) < 60:
        raise HTTPException(
            status_code=409,
            detail=(
                "Refinement prompts are only allowed when the latest preview "
                "quality score is at least 60. Use force=true to override."
            ),
        )

    operator_id = (payload.get("operatorId") or session.get("email") or "").strip()
    if not operator_id:
        raise HTTPException(status_code=400, detail="operatorId is required.")

    prompt_id = await site_repository.submit_refinement_prompt(
        site_id=site_id,
        prompt_text=refinement_prompt,
        operator_id=operator_id,
    )
    if prompt_id is None:
        raise HTTPException(status_code=404, detail="Site not found.")

    generate_request = SiteGenerateRequest(force=force, refinementPromptId=prompt_id)

    try:
        job = await site_repository.queue_generation_job(site_id, request=generate_request)
    except ValueError as exc:
        if str(exc) == "brief_not_approved":
            raise HTTPException(
                status_code=409,
                detail="Approve the site brief before generating a preview.",
            ) from exc
        if str(exc) == "extraction_required":
            raise HTTPException(
                status_code=409,
                detail="Create a site extraction before generating a preview.",
            ) from exc
        raise

    if job is None:
        raise HTTPException(status_code=404, detail="Lead not found.")

    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_regenerate",
        after={
            "jobId": job.id,
            "step": job.step,
            "promptId": prompt_id,
        },
    )
    return success_response(await _job_response(job), meta=response_meta(request))


@router.post(
    "/{site_id}/generate", response_model=ResponseEnvelope[JobResponse], status_code=202
)
async def generate_site(
    site_id: str,
    http_request: Request,
    payload: SiteGenerateRequest | None = None,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[JobResponse]:
    try:
        job = await site_repository.queue_generation_job(site_id, request=payload)
    except ValueError as exc:
        if str(exc) == "brief_not_approved":
            raise HTTPException(
                status_code=409,
                detail="Approve the site brief before generating a preview.",
            ) from exc
        if str(exc) == "extraction_required":
            raise HTTPException(
                status_code=409,
                detail="Create a site extraction before generating a preview.",
            ) from exc
        raise
    if job is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_generate",
        after={"jobId": job.id, "step": job.step},
    )
    return success_response(await _job_response(job), meta=response_meta(http_request))


@router.post(
    "/{site_id}/republish",
    response_model=ResponseEnvelope[JobResponse],
    status_code=202,
)
async def republish_site(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[JobResponse]:
    try:
        job = await site_repository.queue_generation_job(site_id)
    except ValueError as exc:
        if str(exc) == "brief_not_approved":
            raise HTTPException(
                status_code=409,
                detail="Approve the site brief before republishing a preview.",
            ) from exc
        if str(exc) == "extraction_required":
            raise HTTPException(
                status_code=409,
                detail="Create a site extraction before republishing a preview.",
            ) from exc
        raise
    if job is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_republish",
        after={"jobId": job.id, "step": job.step},
    )
    return success_response(await _job_response(job), meta=response_meta(request))


@router.post(
    "/{site_id}/overrides", response_model=ResponseEnvelope[SiteOverrideRecord]
)
async def add_override(
    site_id: str,
    payload: SiteOverrideCreateRequest,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteOverrideRecord]:
    record = await site_repository.create_override(
        site_id, payload, actor=session["email"]
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_override_create",
        after=record.model_dump(),
    )
    return success_response(record, meta=response_meta(http_request))


@router.delete(
    "/{site_id}/overrides/{override_id}",
    response_model=ResponseEnvelope[SiteOverrideRecord],
)
async def disable_override(
    site_id: str,
    override_id: str,
    request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteOverrideRecord]:
    record = await site_repository.disable_override(
        site_id, override_id, actor=session["email"]
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Override not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_override_disable",
        after=record.model_dump(),
    )
    return success_response(record, meta=response_meta(request))


@router.post("/{site_id}/export", response_model=ResponseEnvelope[SiteExportMetadata])
async def export_site(
    site_id: str,
    payload: SiteExportRequest,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteExportMetadata]:
    now = datetime.now(timezone.utc)
    metadata = SiteExportMetadata(
        exportType=payload.exportType,
        repoUrl=payload.repoUrl,
        branch=payload.branch,
        commitSha=payload.commitSha,
        exportPath=payload.exportPath,
        notes=payload.notes,
        createdAt=now,
        updatedAt=now,
    )
    export_metadata = await site_repository.add_export_metadata(site_id, metadata)
    if export_metadata is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_export_create",
        after=export_metadata.model_dump(),
    )
    return success_response(export_metadata, meta=response_meta(http_request))


@router.get(
    "/{site_id}/export", response_model=ResponseEnvelope[SiteExportMetadata | None]
)
async def get_export(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[SiteExportMetadata | None]:
    site = await site_repository.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return success_response(site.exportMetadata, meta=response_meta(request))


@router.get(
    "/{site_id}/export/history", response_model=ResponseEnvelope[list[SiteExportRecord]]
)
async def export_history(
    site_id: str, request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[list[SiteExportRecord]]:
    site = await site_repository.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return success_response(
        await site_repository.list_export_history(site_id), meta=response_meta(request)
    )


@router.get("/{site_id}/export/bundle")
async def download_export_bundle(
    site_id: str, session: dict = Depends(_require_session)
) -> StreamingResponse:
    bundle = await site_repository.build_export_bundle(site_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    filename, payload = bundle
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{site_id}/export/{export_id}/sync",
    response_model=ResponseEnvelope[list[SiteOverrideRecord]],
)
async def sync_export_edits(
    site_id: str,
    export_id: str,
    edits: list[dict[str, Any]],
    request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[list[SiteOverrideRecord]]:
    """
    Syncs local edits back to structured overrides.
    """
    overrides = await site_repository.sync_export_edits(site_id, export_id, edits)
    await write_audit_log(
        session["email"],
        "site",
        site_id,
        "site_export_sync",
        after={"overrideCount": len(overrides)},
    )
    return success_response(overrides, meta=response_meta(request))
