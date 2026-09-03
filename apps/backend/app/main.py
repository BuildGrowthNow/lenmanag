from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.mongo import get_mongo_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        settings.validate_asset_settings()
        logger.info(
            "Asset ingestion configuration: enabled=%s backend=%s retention_days=%s",
            settings.asset_download_enabled,
            settings.asset_storage_backend,
            settings.asset_retention_days,
        )
    except RuntimeError as exc:
        logger.error("Asset ingestion configuration is unhealthy: %s", exc)
    client = get_mongo_client()
    if client is not None:
        try:
            await client.admin.command("ping")
        except Exception as exc:  # pragma: no cover - startup guard for local shell use
            logging.getLogger("lenquant").warning(
                "MongoDB ping failed during startup: %s", exc
            )
    yield
    if client is not None:
        client.close()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception in %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": request.url.path,
        },
    )
