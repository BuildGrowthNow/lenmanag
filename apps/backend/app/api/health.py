from fastapi import APIRouter

from app.core.mongo import get_database
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    database = get_database()
    return HealthResponse(status="ok", mongodb="connected" if database is not None else "not_configured")
