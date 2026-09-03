from fastapi import APIRouter, Depends

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.bundles import router as bundles_router
from app.api.messages import router as messages_router
from app.api.jobs import router as jobs_router
from app.api.leads import router as leads_router
from app.api.health import router as health_router
from app.api.public import router as public_router
from app.api.screenshots import router as screenshots_router
from app.api.static_assets import router as static_assets_router
from app.api.sites import router as sites_router, themes_router
from app.api.users import router as users_router
from app.core.versioning import enforce_api_version
from app.api.assets import router as assets_router
from app.api.metrics import router as metrics_router
from app.api.admin import router as admin_router
from app.api.internal import router as internal_router

api_router = APIRouter()
api_v1_router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(enforce_api_version("1"))]
)

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(sites_router)
api_v1_router.include_router(themes_router)
api_v1_router.include_router(messages_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(public_router)
api_v1_router.include_router(screenshots_router)
api_v1_router.include_router(static_assets_router)
api_v1_router.include_router(bundles_router)
api_v1_router.include_router(assets_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(internal_router)

api_router.include_router(api_v1_router)
