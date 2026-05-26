from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException

from app.core.analytics import analytics_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsEvent, AnalyticsEventCreateRequest, AnalyticsLeadMetrics, AnalyticsSiteMetrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.post("/events", response_model=AnalyticsEvent)
async def ingest_event(request: AnalyticsEventCreateRequest) -> AnalyticsEvent:
    return await analytics_repository.ingest_event(request)


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def dashboard(session: dict = Depends(_require_session)) -> AnalyticsDashboardResponse:
    return await analytics_repository.get_dashboard()


@router.get("/sites/{site_id}", response_model=AnalyticsSiteMetrics | None)
async def site_metrics(site_id: str, session: dict = Depends(_require_session)) -> AnalyticsSiteMetrics | None:
    metrics = await analytics_repository.get_site_metrics(site_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Site metrics not found.")
    return metrics


@router.get("/leads/{lead_id}", response_model=AnalyticsLeadMetrics | None)
async def lead_metrics(lead_id: str, session: dict = Depends(_require_session)) -> AnalyticsLeadMetrics | None:
    metrics = await analytics_repository.get_lead_metrics(lead_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Lead metrics not found.")
    return metrics
