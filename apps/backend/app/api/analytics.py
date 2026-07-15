from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request

from app.core.analytics import analytics_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.core.versioning import response_meta
from app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsEvent, AnalyticsEventCreateRequest, AnalyticsLeadMetrics, AnalyticsSiteMetrics
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.post("/events", response_model=ResponseEnvelope[AnalyticsEvent])
async def ingest_event(payload: AnalyticsEventCreateRequest, request: Request) -> ResponseEnvelope[AnalyticsEvent]:
    event = await analytics_repository.ingest_event(payload)
    return success_response(event, meta=response_meta(request))


@router.get("/dashboard", response_model=ResponseEnvelope[AnalyticsDashboardResponse])
async def dashboard(request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[AnalyticsDashboardResponse]:
    return success_response(await analytics_repository.get_dashboard(), meta=response_meta(request))


@router.get("/sites/{site_id}", response_model=ResponseEnvelope[AnalyticsSiteMetrics])
async def site_metrics(site_id: str, request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[AnalyticsSiteMetrics]:
    metrics = await analytics_repository.get_site_metrics(site_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Site metrics not found.")
    return success_response(metrics, meta=response_meta(request))


@router.get("/leads/{lead_id}", response_model=ResponseEnvelope[AnalyticsLeadMetrics])
async def lead_metrics(lead_id: str, request: Request, session: dict = Depends(_require_session)) -> ResponseEnvelope[AnalyticsLeadMetrics]:
    metrics = await analytics_repository.get_lead_metrics(lead_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Lead metrics not found.")
    return success_response(metrics, meta=response_meta(request))
