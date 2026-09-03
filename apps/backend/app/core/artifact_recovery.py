"""Private, short-lived storage for rejected generation artifacts.

Rejected provider output is useful for debugging, but it must never become a
public preview.  This module stores encrypted JSON outside the public assets
directory and applies the same retention window used by source assets.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _key() -> bytes:
    settings = get_settings()
    secret = (
        settings.rejected_artifact_encryption_key or settings.session_secret
    ).encode()
    return hashlib.sha256(secret).digest()


def _encrypt(value: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise RuntimeError(
            "cryptography is required for rejected artifact storage"
        ) from exc
    nonce = os.urandom(12)
    return nonce + AESGCM(_key()).encrypt(nonce, value, None)


def _storage_root() -> Path:
    """Return a writable private directory for rejected artifacts.

    Production containers run as a non-root user. Older deployments used the
    host-style /var/lib path without mounting or provisioning it, which caused
    the diagnostic write to mask the actual generation failure.
    """
    configured = Path(get_settings().rejected_artifact_path)
    try:
        configured.mkdir(parents=True, exist_ok=True)
        return configured
    except OSError:
        fallback = Path("/tmp/lenquant/rejected-artifacts")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


async def persist_rejected_artifact(
    *,
    lead_id: str,
    site_id: str,
    variant_type: str,
    html: str | None,
    css: str | None,
    js: str | None,
    failure: dict[str, Any],
) -> str:
    """Persist an encrypted rejected artifact and return its private ID."""
    settings = get_settings()
    root = _storage_root()
    artifact_id = hashlib.sha256(
        f"{lead_id}:{site_id}:{variant_type}:{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()[:24]
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.rejected_artifact_retention_days
    )
    payload = {
        "artifactId": artifact_id,
        "leadId": lead_id,
        "siteId": site_id,
        "variantType": variant_type,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": expires.isoformat(),
        "failure": failure,
        "html": html,
        "css": css,
        "js": js,
    }
    path = root / f"{artifact_id}.json.enc"
    path.write_bytes(_encrypt(json.dumps(payload, ensure_ascii=False).encode()))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return artifact_id


def purge_rejected_artifacts() -> int:
    """Remove expired private artifacts; return the number removed."""
    settings = get_settings()
    root = _storage_root()
    if not root.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.rejected_artifact_retention_days
    )
    removed = 0
    for path in root.glob("*.json.enc"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed
