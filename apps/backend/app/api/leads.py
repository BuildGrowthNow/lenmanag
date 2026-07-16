from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.audit import write_audit_log
from app.core.auth_dependencies import CurrentUserId
from app.core.leads import lead_repository
from app.core.versioning import response_meta
from app.schemas.brief import (
    MasterBrief,
    MasterBriefApprovalRequest,
    MasterBriefRefinementRequest,
)
from app.schemas.extraction import (
    ExtractionJobResponse,
    ExtractionSnapshot,
    PageInventoryResponse,
)
from app.schemas.lead import (
    LeadActionResponse,
    LeadDetail,
    LeadImportResponse,
    LeadListResponse,
    LeadPatchRequest,
    LeadUpsertRequest,
)
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=ResponseEnvelope[LeadActionResponse])
async def create_lead(
    user_id: CurrentUserId,
    payload: LeadUpsertRequest,
    http_request: Request,
) -> ResponseEnvelope[LeadActionResponse]:
    result = await lead_repository.create_lead(payload, user_id=user_id)
    await write_audit_log(
        user_id,
        "lead",
        result.lead.id,
        "lead_create",
        after=result.model_dump(),
    )
    return success_response(result, meta=response_meta(http_request))


@router.post("/import", response_model=ResponseEnvelope[LeadImportResponse])
async def import_leads(
    user_id: CurrentUserId,
    http_request: Request,
    file: UploadFile = File(...),
) -> ResponseEnvelope[LeadImportResponse]:
    raw = await file.read()
    try:
        result = await lead_repository.import_csv(
            file_name=file.filename, csv_bytes=raw, user_id=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await write_audit_log(
        user_id,
        "lead_import",
        result.job.id,
        "lead_import",
        after=result.model_dump(),
    )
    return success_response(result, meta=response_meta(http_request))


@router.get("", response_model=ResponseEnvelope[LeadListResponse])
async def list_leads(
    user_id: CurrentUserId,
    http_request: Request,
    q: str | None = None,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> ResponseEnvelope[LeadListResponse]:
    try:
        result = await lead_repository.list_leads(
            q=q, status=status, limit=limit, offset=offset, user_id=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(result, meta=response_meta(http_request))


@router.get("/{lead_id}", response_model=ResponseEnvelope[LeadDetail])
async def get_lead(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[LeadDetail]:
    lead = await lead_repository.get_lead(lead_id, user_id=user_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(lead, meta=response_meta(http_request))


@router.patch("/{lead_id}", response_model=ResponseEnvelope[LeadDetail])
async def patch_lead(
    lead_id: str,
    user_id: CurrentUserId,
    payload: LeadPatchRequest,
    http_request: Request,
) -> ResponseEnvelope[LeadDetail]:
    lead = await lead_repository.update_lead(lead_id, payload, user_id=user_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "lead_update",
        after=lead.model_dump(),
    )
    return success_response(lead, meta=response_meta(http_request))


@router.delete("/{lead_id}", response_model=ResponseEnvelope[LeadDetail])
async def delete_lead(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[LeadDetail]:
    lead = await lead_repository.delete_lead(lead_id, user_id=user_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "lead_archive",
        after=lead.model_dump(),
    )
    return success_response(lead, meta=response_meta(http_request))


@router.post(
    "/{lead_id}/extraction/start",
    response_model=ResponseEnvelope[ExtractionJobResponse],
)
async def start_extraction(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[ExtractionJobResponse]:
    result = await lead_repository.start_extraction(lead_id, refresh=False)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "site_extraction_start",
        after=result.model_dump(),
    )
    return success_response(result, meta=response_meta(http_request))


@router.post(
    "/{lead_id}/extraction/refresh",
    response_model=ResponseEnvelope[ExtractionJobResponse],
)
async def refresh_extraction(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[ExtractionJobResponse]:
    result = await lead_repository.start_extraction(lead_id, refresh=True)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "site_extraction_refresh",
        after=result.model_dump(),
    )
    return success_response(result, meta=response_meta(http_request))


@router.get(
    "/{lead_id}/extraction", response_model=ResponseEnvelope[ExtractionSnapshot]
)
async def get_extraction(
    lead_id: str, _user_id: CurrentUserId, http_request: Request
) -> ResponseEnvelope[ExtractionSnapshot]:
    extraction = await lead_repository.get_extraction(lead_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(extraction, meta=response_meta(http_request))


@router.get("/{lead_id}/pages", response_model=ResponseEnvelope[PageInventoryResponse])
async def get_pages(
    lead_id: str, _user_id: CurrentUserId, http_request: Request
) -> ResponseEnvelope[PageInventoryResponse]:
    pages = await lead_repository.list_pages(lead_id)
    if pages is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(pages, meta=response_meta(http_request))


# Master Brief Endpoints (AI-Native)


@router.get(
    "/{lead_id}/master-brief", response_model=ResponseEnvelope[MasterBrief | None]
)
async def get_master_brief(
    lead_id: str,
    _user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief | None]:
    master_brief = await lead_repository.get_master_brief(lead_id)
    return success_response(master_brief, meta=response_meta(http_request))


@router.post("/{lead_id}/master-brief", response_model=ResponseEnvelope[MasterBrief])
async def create_master_brief(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief]:
    try:
        master_brief = await lead_repository.create_master_brief(lead_id)
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(
                status_code=409,
                detail="Create a site extraction before generating the brief.",
            ) from exc
        raise
    if master_brief is None:
        raise HTTPException(status_code=500, detail="Failed to generate master brief.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "master_brief_create",
        after=master_brief.model_dump(),
    )
    return success_response(master_brief, meta=response_meta(http_request))


@router.post(
    "/{lead_id}/master-brief/refine", response_model=ResponseEnvelope[MasterBrief]
)
async def refine_master_brief(
    lead_id: str,
    user_id: CurrentUserId,
    payload: MasterBriefRefinementRequest,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief]:
    try:
        master_brief = await lead_repository.refine_master_brief(
            lead_id=lead_id,
            feedback=payload.feedback,
        )
    except ValueError as exc:
        if str(exc) == "no_existing_brief":
            raise HTTPException(
                status_code=404,
                detail="No existing brief to refine. Create one first.",
            ) from exc
        raise
    if master_brief is None:
        raise HTTPException(status_code=500, detail="Failed to refine master brief.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "master_brief_refine",
        after={"feedback": payload.feedback, "version": master_brief.version},
    )
    return success_response(master_brief, meta=response_meta(http_request))


@router.post(
    "/{lead_id}/master-brief/approve", response_model=ResponseEnvelope[MasterBrief]
)
async def approve_master_brief(
    lead_id: str,
    user_id: CurrentUserId,
    payload: MasterBriefApprovalRequest,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief]:
    try:
        master_brief = await lead_repository.approve_master_brief(
            lead_id=lead_id,
            approved_by=payload.approvedBy or user_id,
            notes=payload.notes,
        )
    except ValueError as exc:
        if str(exc) == "no_existing_brief":
            raise HTTPException(status_code=404, detail="Brief not found.") from exc
        raise
    if master_brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "master_brief_approve",
        after=master_brief.model_dump(),
    )
    return success_response(master_brief, meta=response_meta(http_request))
