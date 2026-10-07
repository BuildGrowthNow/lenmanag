from fastapi import APIRouter, Request

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
