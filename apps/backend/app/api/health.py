from typing import Optional
from fastapi import APIRouter, Request, Header

from app.core.mongo import get_database
from app.core.versioning import response_meta
from app.schemas.health import HealthResponse
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ResponseEnvelope[HealthResponse])
async def health(request: Request) -> ResponseEnvelope[HealthResponse]:
    database = get_database()
    payload = HealthResponse(
        status="ok", mongodb="connected" if database is not None else "not_configured"
    )
    return success_response(payload, meta=response_meta(request))


@router.get("/test-auth", response_model=ResponseEnvelope[dict])
async def test_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> ResponseEnvelope[dict]:
    return success_response(
        {"authorization_header": authorization or "none", "all_headers": dict(request.headers)},
        meta=response_meta(request),
    )
