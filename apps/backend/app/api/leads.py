from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.core.audit import write_audit_log
from app.core.auth_dependencies import CurrentUserId
from app.core.leads import lead_repository
from app.core.config import get_settings
from app.core.versioning import response_meta
from app.schemas.brief import (
    MasterBrief,
    MasterBriefApprovalRequest,
    MasterBriefBrandAssetsPatch,
    MasterBriefRefinementRequest,
    PreflightAssetAction,
)
from app.schemas.extraction import (
    ExtractionAnalysisResponse,
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
from app.schemas.site import ClientShareRequest, ClientShareResponse
from app.schemas.response import ResponseEnvelope, success_response

logger = logging.getLogger(__name__)

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
    mode: str | None = Form(None),
) -> ResponseEnvelope[LeadImportResponse]:
    raw = await file.read()
    pipeline_mode = mode if mode in {"auto", "manual"} else "auto"
    try:
        result = await lead_repository.import_csv(
            file_name=file.filename,
            csv_bytes=raw,
            user_id=user_id,
            pipeline_mode=pipeline_mode,
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
    stage: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> ResponseEnvelope[LeadListResponse]:
    try:
        result = await lead_repository.list_leads(
            q=q, status=status, stage=stage, limit=limit, offset=offset, user_id=user_id
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


@router.get(
    "/{lead_id}/client-link",
    response_model=ResponseEnvelope[ClientShareResponse | None],
)
async def get_client_link(
    lead_id: str, user_id: CurrentUserId, http_request: Request
) -> ResponseEnvelope[ClientShareResponse | None]:
    share = await lead_repository.get_client_share(lead_id, user_id)
    if (
        share is None
        and await lead_repository.get_lead(lead_id, user_id=user_id) is None
    ):
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(share, meta=response_meta(http_request))


@router.put(
    "/{lead_id}/client-link", response_model=ResponseEnvelope[ClientShareResponse]
)
async def save_client_link(
    lead_id: str,
    payload: ClientShareRequest,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[ClientShareResponse]:
    try:
        share = await lead_repository.save_client_share(
            lead_id, payload.siteIds, user_id, payload.bookingUrl
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if share is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(
        ClientShareResponse.model_validate(share), meta=response_meta(http_request)
    )


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


@router.delete("/{lead_id}/permanent", response_model=ResponseEnvelope[dict[str, bool]])
async def permanently_delete_lead(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[dict[str, bool]]:
    deleted = await lead_repository.permanently_delete_lead(lead_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response({"deleted": True}, meta=response_meta(http_request))


@router.post(
    "/{lead_id}/extraction/start",
    response_model=ResponseEnvelope[ExtractionJobResponse],
)
async def start_extraction(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[ExtractionJobResponse]:
    result = await lead_repository.start_extraction(
        lead_id, refresh=False, user_id=user_id
    )
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
    result = await lead_repository.start_extraction(
        lead_id, refresh=True, user_id=user_id
    )
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
    lead_id: str, user_id: CurrentUserId, http_request: Request
) -> ResponseEnvelope[ExtractionSnapshot]:
    extraction = await lead_repository.get_extraction(lead_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(extraction, meta=response_meta(http_request))


@router.get("/{lead_id}/preflight", response_model=ResponseEnvelope[dict[str, Any]])
async def get_generation_preflight(
    lead_id: str, user_id: CurrentUserId, http_request: Request
) -> ResponseEnvelope[dict[str, Any]]:
    """Expose evidence, assets, fallbacks, and runtime choices before generation."""
    lead = await lead_repository.get_lead(lead_id, user_id=user_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    extraction = await lead_repository.get_extraction(lead_id)
    brief = await lead_repository.get_master_brief(lead_id)
    assets = brief.brandAssets.model_dump(mode="json") if brief else {}
    cues = [
        cue.model_dump(mode="json")
        for cue in (extraction.brandAssetCues if extraction else [])
    ]
    rejected = [cue for cue in cues if "download_error" in str(cue.get("note") or "")]
    source_only = [
        cue
        for cue in cues
        if cue.get("value") and not cue.get("cachedUrl") and cue not in rejected
    ]
    settings = get_settings()
    variants = getattr(lead, "generationTypes", []) or []
    return success_response(
        {
            "leadId": lead_id,
            "assetDownload": {
                "enabled": settings.asset_download_enabled,
                "backend": settings.asset_storage_backend,
                "healthy": settings.asset_download_enabled,
            },
            "selectedLogo": assets.get("logoUrl"),
            "logoVariants": assets.get("logoVariants", []),
            "heroCandidates": assets.get("imageInventory", [])[:8],
            "projectAssets": assets.get("imageInventory", []),
            "rejectedAssets": rejected,
            "sourceOnlyAssets": source_only,
            "proofEvidence": (
                brief.extractedContent.get("testimonials", []) if brief else []
            ),
            "missingRequirements": list(
                brief.missingRequirements if brief else ["extraction_required"]
            ),
            "intentionalFallbacks": ["typography_only"]
            if brief and "approved_hero_or_project_images" in brief.missingRequirements
            else [],
            "runtimeModes": {
                variant: "enhanced_html"
                for variant in variants
                if variant.startswith("html_")
            },
        },
        meta=response_meta(http_request),
    )


@router.post(
    "/{lead_id}/preflight/assets", response_model=ResponseEnvelope[MasterBrief]
)
async def update_preflight_asset(
    lead_id: str,
    payload: PreflightAssetAction,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief]:
    """Approve, reject, or re-role a cached asset before generation."""
    brief = await lead_repository.get_master_brief(lead_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    assets = brief.brandAssets.model_dump(mode="json")
    inventory = list(assets.get("imageInventory") or [])
    match = next(
        (
            item
            for item in inventory
            if item.get("url") == payload.sourceUrl
            or item.get("sourceUrl") == payload.sourceUrl
        ),
        None,
    )
    if match is None:
        raise HTTPException(
            status_code=404, detail="Asset not found in preflight inventory."
        )
    if payload.action == "approve":
        if not str(match.get("url") or "").startswith(
            ("https://", "/api/internal/assets/", "data:")
        ):
            raise HTTPException(
                status_code=409, detail="Asset must be cached before approval."
            )
        match["approved"] = True
        if match["url"] not in assets.get("imageUrls", []):
            assets.setdefault("imageUrls", []).append(match["url"])
    elif payload.action == "reject":
        inventory = [item for item in inventory if item is not match]
        assets["imageUrls"] = [
            url for url in assets.get("imageUrls", []) if url != payload.sourceUrl
        ]
    else:
        if not payload.role:
            raise HTTPException(
                status_code=422, detail="role is required for re-role action."
            )
        match["role"] = payload.role
    updated = await lead_repository.update_master_brief_assets(
        lead_id,
        {"imageInventory": inventory, "imageUrls": assets.get("imageUrls", [])},
        user_id=user_id,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    return success_response(updated, meta=response_meta(http_request))


@router.get("/{lead_id}/pages", response_model=ResponseEnvelope[PageInventoryResponse])
async def get_pages(
    lead_id: str, user_id: CurrentUserId, http_request: Request
) -> ResponseEnvelope[PageInventoryResponse]:
    pages = await lead_repository.list_pages(lead_id)
    if pages is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return success_response(pages, meta=response_meta(http_request))


# Analysis Endpoints


@router.post(
    "/{lead_id}/analysis/start",
    response_model=ResponseEnvelope[ExtractionJobResponse],
)
async def start_lead_analysis(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[ExtractionJobResponse]:
    """Re-run LLM analysis on existing extraction data without re-crawling."""
    try:
        result = await lead_repository.start_analysis_refresh(lead_id, user_id=user_id)
    except ValueError as exc:
        if str(exc) == "extraction_not_completed":
            raise HTTPException(
                status_code=400,
                detail="Extraction must be completed before running analysis.",
            ) from exc
        raise
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "analysis_refresh_start",
        after=result.model_dump(),
    )
    return success_response(result, meta=response_meta(http_request))


@router.get(
    "/{lead_id}/analysis",
    response_model=ResponseEnvelope[ExtractionAnalysisResponse],
)
async def get_lead_analysis(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[ExtractionAnalysisResponse]:
    """Get the latest LLM analysis for a lead's extraction."""
    analysis_response = await lead_repository.get_analysis(lead_id, user_id=user_id)
    if analysis_response is None:
        raise HTTPException(
            status_code=404, detail="No analysis available for this lead."
        )
    return success_response(analysis_response, meta=response_meta(http_request))


# Master Brief Endpoints (AI-Native)


@router.get(
    "/{lead_id}/master-brief", response_model=ResponseEnvelope[MasterBrief | None]
)
async def get_master_brief(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief | None]:
    lead = await lead_repository.get_lead(lead_id, user_id=user_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
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
        if str(exc).startswith("brief_requirements_unresolved:"):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
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


@router.patch(
    "/{lead_id}/master-brief/assets", response_model=ResponseEnvelope[MasterBrief]
)
async def update_master_brief_assets(
    lead_id: str,
    user_id: CurrentUserId,
    payload: MasterBriefBrandAssetsPatch,
    http_request: Request,
) -> ResponseEnvelope[MasterBrief]:
    brief = await lead_repository.update_master_brief_assets(
        lead_id, payload.model_dump(exclude_unset=True), user_id=user_id
    )
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    await write_audit_log(
        user_id,
        "lead",
        lead_id,
        "master_brief_assets_updated",
        after=payload.model_dump(exclude_unset=True),
    )
    return success_response(brief, meta=response_meta(http_request))
