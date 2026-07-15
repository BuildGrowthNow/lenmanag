from __future__ import annotations

import hmac
import hashlib
import os
import mimetypes
from datetime import datetime
from fastapi import APIRouter, Response, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import get_settings

router = APIRouter(prefix="/api/internal/assets")
settings = get_settings()


@router.get("/local/{relpath}")
def serve_local_asset(relpath: str, exp: int = Query(...), sig: str = Query(...)):
    # validate expiry
    now = int(datetime.utcnow().timestamp())
    if now > int(exp):
        raise HTTPException(status_code=410, detail="signed url expired")

    payload = f"{relpath}:{exp}".encode("utf-8")
    key = settings.session_secret.encode("utf-8")
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=403, detail="invalid signature")

    base = os.path.abspath(settings.asset_local_path)
    # sanitize
    name = os.path.basename(relpath)
    path = os.path.join(base, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="not found")

    ctype, _ = mimetypes.guess_type(path)
    return FileResponse(path, media_type=ctype or "application/octet-stream")
