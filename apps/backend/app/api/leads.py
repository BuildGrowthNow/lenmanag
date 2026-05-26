from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, UploadFile

from app.core.audit import write_audit_log
from app.core.leads import lead_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.schemas.brief import SiteBrief, SiteBriefPatchRequest
from app.schemas.extraction import ExtractionJobResponse, ExtractionSnapshot, PageInventoryResponse
from app.schemas.lead import LeadActionResponse, LeadDetail, LeadImportResponse, LeadListResponse, LeadPatchRequest, LeadUpsertRequest

router = APIRouter(prefix="/leads", tags=["leads"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.post("", response_model=LeadActionResponse)
async def create_lead(request: LeadUpsertRequest, session: dict = Depends(_require_session)) -> LeadActionResponse:
    result = await lead_repository.create_lead(request)
    await write_audit_log(session["email"], "lead", result.lead.id, "lead_create", after=result.model_dump())
    return result


@router.post("/import", response_model=LeadImportResponse)
async def import_leads(
    file: UploadFile = File(...),
    session: dict = Depends(_require_session),
) -> LeadImportResponse:
    raw = await file.read()
    try:
        result = await lead_repository.import_csv(file_name=file.filename, csv_bytes=raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await write_audit_log(session["email"], "lead_import", result.job.id, "lead_import", after=result.model_dump())
    return result


@router.get("", response_model=LeadListResponse)
async def list_leads(
    q: str | None = None,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
    session: dict = Depends(_require_session),
) -> LeadListResponse:
    return await lead_repository.list_leads(q=q, status=status, limit=limit, offset=offset)


@router.get("/{lead_id}")
async def get_lead(lead_id: str, session: dict = Depends(_require_session)) -> LeadDetail:
    lead = await lead_repository.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


@router.patch("/{lead_id}")
async def patch_lead(lead_id: str, request: LeadPatchRequest, session: dict = Depends(_require_session)) -> LeadDetail:
    lead = await lead_repository.update_lead(lead_id, request)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "lead_update", after=lead.model_dump())
    return lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, session: dict = Depends(_require_session)) -> LeadDetail:
    lead = await lead_repository.delete_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "lead_archive", after=lead.model_dump())
    return lead


@router.post("/{lead_id}/extraction/start", response_model=ExtractionJobResponse)
async def start_extraction(lead_id: str, session: dict = Depends(_require_session)) -> ExtractionJobResponse:
    result = await lead_repository.start_extraction(lead_id, refresh=False)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_extraction_start", after=result.model_dump())
    return result


@router.post("/{lead_id}/extraction/refresh", response_model=ExtractionJobResponse)
async def refresh_extraction(lead_id: str, session: dict = Depends(_require_session)) -> ExtractionJobResponse:
    result = await lead_repository.start_extraction(lead_id, refresh=True)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_extraction_refresh", after=result.model_dump())
    return result


@router.get("/{lead_id}/extraction", response_model=ExtractionSnapshot)
async def get_extraction(lead_id: str, session: dict = Depends(_require_session)) -> ExtractionSnapshot:
    extraction = await lead_repository.get_extraction(lead_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return extraction


@router.get("/{lead_id}/pages", response_model=PageInventoryResponse)
async def get_pages(lead_id: str, session: dict = Depends(_require_session)) -> PageInventoryResponse:
    pages = await lead_repository.list_pages(lead_id)
    if pages is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return pages


@router.get("/{lead_id}/brief", response_model=SiteBrief | None)
async def get_brief(lead_id: str, session: dict = Depends(_require_session)) -> SiteBrief | None:
    return await lead_repository.get_brief(lead_id)


@router.post("/{lead_id}/brief", response_model=SiteBrief)
async def create_brief(lead_id: str, session: dict = Depends(_require_session)) -> SiteBrief:
    try:
        brief = await lead_repository.create_brief(lead_id)
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(status_code=409, detail="Create a site extraction before generating a brief.") from exc
        raise
    if brief is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_brief_create", after=brief.model_dump())
    return brief


@router.patch("/{lead_id}/brief", response_model=SiteBrief)
async def update_brief(lead_id: str, request: SiteBriefPatchRequest, session: dict = Depends(_require_session)) -> SiteBrief:
    try:
        brief = await lead_repository.update_brief(lead_id, request)
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(status_code=409, detail="Create a site extraction before updating the brief.") from exc
        raise
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_brief_update", after=brief.model_dump())
    return brief


@router.post("/{lead_id}/brief/approve", response_model=SiteBrief)
async def approve_brief(lead_id: str, session: dict = Depends(_require_session)) -> SiteBrief:
    try:
        brief = await lead_repository.approve_brief(lead_id, approved_by=session["email"])
    except ValueError as exc:
        if str(exc) == "brief_requires_extraction":
            raise HTTPException(status_code=409, detail="Create a site extraction before approving the brief.") from exc
        raise
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    await write_audit_log(session["email"], "lead", lead_id, "site_brief_approve", after=brief.model_dump())
    return brief
