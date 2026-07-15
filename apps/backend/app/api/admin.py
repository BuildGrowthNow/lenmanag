from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Request

from app.core.security import decode_session_token
from app.core.audit import write_audit_log
from app.core.admin_config import get_config, patch_config
from app.core.versioning import response_meta

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(session_cookie: str | None) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_session_token(session_cookie)
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    # accept operator or admin roles
    if payload.get("role") not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="forbidden")
    return payload


@router.get("/config")
async def get_admin_config(request: Request, session_cookie: str | None = Cookie(default=None)):
    user = _require_admin(session_cookie)
    cfg = await get_config()
    await write_audit_log(user.get("email"), "admin", "config", "get_config", after={"returned_keys": list(cfg.keys())})
    return {"data": cfg, "meta": response_meta(request)}


@router.patch("/config")
async def patch_admin_config(request: Request, payload: dict, session_cookie: str | None = Cookie(default=None)):
    user = _require_admin(session_cookie)
    before = await get_config()
    # basic validation: only allow whitelisted keys
    allowed = {"asset_storage_backend", "asset_max_file_bytes", "asset_max_aggregate_bytes", "asset_retention_days", "asset_gcp_signed_url_expiry", "asset_concurrent_downloads", "asset_download_timeout"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="no valid configuration keys provided")
    updated = await patch_config(updates)
    await write_audit_log(user.get("email"), "admin", "config", "patch_config", before=before, after=updated)
    return {"data": updated, "meta": response_meta(request)}
