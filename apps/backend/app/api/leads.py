from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Request, UploadFile

from app.core.audit import write_audit_log
from app.core.leads import lead_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.core.versioning import response_meta
from app.schemas.brief import SiteBrief, SiteBriefPatchRequest
from app.schemas.extraction import ExtractionJobResponse, ExtractionSnapshot, PageInventoryResponse
from app.schemas.lead import LeadActionResponse, LeadDetail, LeadImportResponse, LeadListResponse, LeadPatchRequest, LeadUpsertRequest
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(prefix="/leads", tags=["leads"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.post("", response_model=ResponseEnvelope[LeadActionResponse])
async def create_lead(
    payload: LeadUpsertRequest,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[LeadActionResponse]:
    result = await lead_repository.create_lead(payload)
    await write_audit_log(session["email"], "lead", result.lead.id, "lead_create", after=result.model_dump())
    return success_response(result, meta=response_meta(http_request))


@router.post("/import", response_model=ResponseEnvelope[LeadImportResponse])
async def import_leads(
    http_request: Request,
    file: UploadFile = File(...),
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[LeadImportResponse]:
    raw = await file.read()
    try:
        result = await lead_repository.import_csv(file_name=file.filename, csv_bytes=raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await write_audit_log(session["email"], "lead_import", result.job.id, "lead_import", after=result.model_dump())
    return success_response(result, meta=response_meta(http_request))


@router.get("", response_model=ResponseEnvelope[LeadListResponse])
async def list_leads(
    http_request: Request,
    q: str | None = None,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[LeadListResponse]:
    result = await lead_repository.list_leads(q=q, status=status, limit=limit, offset=offset)
    return success_response(result, meta=response_meta(http_request))


@router.get("/{lead_id}", response_model=ResponseEnvelope[LeadDetail])
async def get_lead(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[LeadDetail]:
    lead = await lead_repository.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(lead, meta=response_meta(http_request))


@router.patch("/{lead_id}", response_model=ResponseEnvelope[LeadDetail])
async def patch_lead(
    lead_id: str,
    payload: LeadPatchRequest,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[LeadDetail]:
    lead = await lead_repository.update_lead(lead_id, payload)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "lead_update", after=lead.model_dump())
    return success_response(lead, meta=response_meta(http_request))


@router.delete("/{lead_id}", response_model=ResponseEnvelope[LeadDetail])
async def delete_lead(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[LeadDetail]:
    lead = await lead_repository.delete_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "lead_archive", after=lead.model_dump())
    return success_response(lead, meta=response_meta(http_request))


@router.post("/{lead_id}/extraction/start", response_model=ResponseEnvelope[ExtractionJobResponse])
async def start_extraction(
    lead_id: str,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[ExtractionJobResponse]:
    result = await lead_repository.start_extraction(lead_id, refresh=False)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_extraction_start", after=result.model_dump())
    return success_response(result, meta=response_meta(http_request))


@router.post("/{lead_id}/extraction/refresh", response_model=ResponseEnvelope[ExtractionJobResponse])
async def refresh_extraction(
    lead_id: str,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[ExtractionJobResponse]:
    result = await lead_repository.start_extraction(lead_id, refresh=True)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_extraction_refresh", after=result.model_dump())
    return success_response(result, meta=response_meta(http_request))


@router.get("/{lead_id}/extraction", response_model=ResponseEnvelope[ExtractionSnapshot])
async def get_extraction(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[ExtractionSnapshot]:
    extraction = await lead_repository.get_extraction(lead_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(extraction, meta=response_meta(http_request))


@router.get("/{lead_id}/pages", response_model=ResponseEnvelope[PageInventoryResponse])
async def get_pages(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[PageInventoryResponse]:
    pages = await lead_repository.list_pages(lead_id)
    if pages is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(pages, meta=response_meta(http_request))


@router.get("/{lead_id}/brief", response_model=ResponseEnvelope[SiteBrief | None])
async def get_brief(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[SiteBrief | None]:
    brief = await lead_repository.get_brief(lead_id)
    return success_response(brief, meta=response_meta(http_request))


@router.post("/{lead_id}/brief", response_model=ResponseEnvelope[SiteBrief])
async def create_brief(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[SiteBrief]:
    try:
        brief = await lead_repository.create_brief(lead_id)
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(status_code=409, detail="Create a site extraction before generating a brief.") from exc
        raise
    if brief is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_brief_create", after=brief.model_dump())
    return success_response(brief, meta=response_meta(http_request))


@router.patch("/{lead_id}/brief", response_model=ResponseEnvelope[SiteBrief])
async def update_brief(
    lead_id: str,
    payload: SiteBriefPatchRequest,
    http_request: Request,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[SiteBrief]:
    try:
        brief = await lead_repository.update_brief(lead_id, payload)
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(status_code=409, detail="Create a site extraction before updating the brief.") from exc
        raise
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_brief_update", after=brief.model_dump())
    return success_response(brief, meta=response_meta(http_request))


@router.post("/{lead_id}/brief/approve", response_model=ResponseEnvelope[SiteBrief])
async def approve_brief(lead_id: str, http_request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[SiteBrief]:
    try:
        brief = await lead_repository.approve_brief(lead_id, approved_by=session["email"])
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(status_code=409, detail="Create a site extraction before approving the brief.") from exc
        if str(exc) == "brief_requires_critical_gaps_resolved":
            raise HTTPException(status_code=409, detail="Resolve critical extraction gaps before approving the brief.") from exc
        raise
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_brief_approve", after=brief.model_dump())
    return success_response(brief, meta=response_meta(http_request))
