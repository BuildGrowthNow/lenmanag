from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from app.core.mongo import get_database
from app.core.config import get_settings

COLLECTION = "app_config"
DOC_ID = "asset_settings"


async def get_config() -> Dict[str, Any]:
    db = get_database()
    doc = await db[COLLECTION].find_one({"_id": DOC_ID})
    settings = get_settings()
    base = {
        "asset_storage_backend": settings.asset_storage_backend,
        "asset_max_file_bytes": settings.asset_max_file_bytes,
        "asset_max_aggregate_bytes": settings.asset_max_aggregate_bytes,
        "asset_retention_days": settings.asset_retention_days,
        "asset_gcp_signed_url_expiry": settings.asset_gcp_signed_url_expiry,
        "asset_concurrent_downloads": settings.asset_concurrent_downloads,
        "asset_download_timeout": settings.asset_download_timeout,
    }
    if doc:
        base.update(doc.get("value", {}))
    return base


async def patch_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    db = get_database()
    now = datetime.utcnow()
    await db[COLLECTION].update_one(
        {"_id": DOC_ID}, {"$set": {"value": updates, "updatedAt": now}}, upsert=True
    )
    return updates
