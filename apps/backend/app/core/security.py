import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from app.core.config import get_settings

settings = get_settings()

SESSION_COOKIE_NAME = "lenquant_session"
SESSION_TTL_SECONDS = settings.session_cookie_max_age_seconds


def _secret_bytes() -> bytes:
    return settings.session_secret.encode("utf-8")


def _sign(payload: str) -> str:
    signature = hmac.new(_secret_bytes(), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")


def create_session_token(email: str, name: Optional[str] = None, role: str = "operator") -> str:
    now = int(time.time())
    payload = {
        "email": email.lower(),
        "name": name or email.split("@", 1)[0],
        "role": role,
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"{encoded}.{_sign(encoded)}"


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        encoded, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(encoded)):
            return None
        padding = "=" * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
        payload = json.loads(raw)
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

