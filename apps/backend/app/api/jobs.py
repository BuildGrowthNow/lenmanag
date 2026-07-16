from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request

from app.core.leads import lead_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.core.versioning import response_meta
from app.schemas.job import JobQueueHealthResponse, JobResponse
from app.schemas.lead import JobRetryRequest
from app.schemas.response import ResponseEnvelope, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _require_session(
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.get("/health", response_model=ResponseEnvelope[JobQueueHealthResponse])
async def queue_health(
    http_request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[JobQueueHealthResponse]:
    return success_response(
        await lead_repository.get_queue_health(), meta=response_meta(http_request)
    )


@router.get("/{job_id}", response_model=ResponseEnvelope[JobResponse])
async def get_job(
    job_id: str, http_request: Request, session: dict = Depends(_require_session)
) -> ResponseEnvelope[JobResponse]:
    job = await lead_repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_doc = await lead_repository.get_job_doc(job_id)
    if job_doc is None:
        logger.warning("Job summary exists but document missing for job_id=%s", job_id)
    lead_ids = list(job_doc.get("leadIds", [])) if job_doc else []
    metadata = dict(job_doc.get("metadata", {})) if job_doc else {}
    return success_response(
        JobResponse(job=job, leadIds=lead_ids, metadata=metadata),
        meta=response_meta(http_request),
    )


@router.post("/{job_id}/retry", response_model=ResponseEnvelope[JobResponse])
async def retry_job(
    job_id: str,
    http_request: Request,
    payload: JobRetryRequest | None = None,
    session: dict = Depends(_require_session),
) -> ResponseEnvelope[JobResponse]:
    retry = await lead_repository.retry_job(job_id, request=payload)
    if retry is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_doc = await lead_repository.get_job_doc(retry.id)
    lead_ids = list(job_doc.get("leadIds", [])) if job_doc else []
    metadata = dict(job_doc.get("metadata", {})) if job_doc else {}
    return success_response(
        JobResponse(job=retry, leadIds=lead_ids, metadata=metadata),
        meta=response_meta(http_request),
    )
