from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.messages import router as messages_router
from app.api.jobs import router as jobs_router
from app.api.leads import router as leads_router
from app.api.health import router as health_router
from app.api.sites import router as sites_router, themes_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/api")
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(leads_router, prefix="/api")
api_router.include_router(jobs_router, prefix="/api")
api_router.include_router(sites_router, prefix="/api")
api_router.include_router(themes_router, prefix="/api")
api_router.include_router(messages_router, prefix="/api")
api_router.include_router(analytics_router, prefix="/api")
