from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.core.config import get_settings

settings = get_settings()


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.jwt_expiry_hours)

    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
