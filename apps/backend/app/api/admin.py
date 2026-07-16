from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.auth_dependencies import CurrentUserId
from app.core.audit import write_audit_log
from app.core.admin_config import get_config, patch_config
from app.core.versioning import response_meta

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config")
async def get_admin_config(request: Request, user_id: CurrentUserId):
    cfg = await get_config()
    await write_audit_log(
        user_id,
        "admin",
        "config",
        "get_config",
        after={"returned_keys": list(cfg.keys())},
    )
    return {"data": cfg, "meta": response_meta(request)}


@router.patch("/config")
async def patch_admin_config(request: Request, payload: dict, user_id: CurrentUserId):
    before = await get_config()
    allowed = {
        "asset_storage_backend",
        "asset_max_file_bytes",
        "asset_max_aggregate_bytes",
        "asset_retention_days",
        "asset_gcp_signed_url_expiry",
        "asset_concurrent_downloads",
        "asset_download_timeout",
    }
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(
            status_code=400, detail="no valid configuration keys provided"
        )
    updated = await patch_config(updates)
    await write_audit_log(
        user_id,
        "admin",
        "config",
        "patch_config",
        before=before,
        after=updated,
    )
    return {"data": updated, "meta": response_meta(request)}
