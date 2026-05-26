from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.mongo import get_mongo_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_mongo_client()
    if client is not None:
        try:
            await client.admin.command("ping")
        except Exception as exc:  # pragma: no cover - startup guard for local shell use
            logging.getLogger("lenquant").warning("MongoDB ping failed during startup: %s", exc)
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
