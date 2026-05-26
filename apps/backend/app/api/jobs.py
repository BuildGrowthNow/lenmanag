from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException

from app.core.leads import lead_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.schemas.job import JobQueueHealthResponse, JobResponse
from app.schemas.lead import JobRetryRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: dict = Depends(_require_session)) -> JobResponse:
    job = await lead_repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_doc = await lead_repository.get_job_doc(job_id)
    lead_ids = list(job_doc.get("leadIds", [])) if job_doc else []
    metadata = dict(job_doc.get("metadata", {})) if job_doc else {}
    return JobResponse(job=job, leadIds=lead_ids, metadata=metadata)


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: str, request: JobRetryRequest | None = None, session: dict = Depends(_require_session)) -> JobResponse:
    retry = await lead_repository.retry_job(job_id, request=request)
    if retry is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_doc = await lead_repository.get_job_doc(retry.id)
    lead_ids = list(job_doc.get("leadIds", [])) if job_doc else []
    metadata = dict(job_doc.get("metadata", {})) if job_doc else {}
    return JobResponse(job=retry, leadIds=lead_ids, metadata=metadata)


@router.get("/health", response_model=JobQueueHealthResponse)
async def queue_health(session: dict = Depends(_require_session)) -> JobQueueHealthResponse:
    return await lead_repository.get_queue_health()
