from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Response

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.security import SESSION_COOKIE_NAME, create_session_token, decode_session_token
from app.schemas.auth import AuthDecisionResponse, LoginRequest, LoginResponse, SessionResponse, SessionUser, VerificationRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _is_allowlisted(email: str) -> tuple[bool, str | None]:
    settings = get_settings()
    normalized = _normalize_email(email)
    if normalized in settings.allowlist_emails:
        return True, None
    if "@" in normalized:
        domain = normalized.split("@", 1)[1]
        if domain in settings.allowlist_domains:
            return True, None
    return False, "email_not_allowlisted"


@router.post("/verify", response_model=AuthDecisionResponse)
async def verify_login(request: VerificationRequest) -> AuthDecisionResponse:
    allowed, reason = _is_allowlisted(request.email)
    await write_audit_log(None, "auth", _normalize_email(str(request.email)), "verify_login", after={"allowed": allowed, "reason": reason})
    return AuthDecisionResponse(allowed=allowed, reason=reason, email=request.email)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response) -> LoginResponse:
    allowed, reason = _is_allowlisted(request.email)
    email = _normalize_email(str(request.email))
    if not allowed:
        await write_audit_log(None, "auth", email, "login_denied", after={"reason": reason})
        return LoginResponse(authenticated=False, user=None, status="denied", message="Access denied. This email is not on the admin allowlist.")

    token = create_session_token(email=email, name=request.name)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 8,
        path="/",
    )
    user = SessionUser(email=email, name=request.name or email.split("@", 1)[0], role="operator")
    await write_audit_log(email, "auth", email, "login_success", after={"email": email})
    return LoginResponse(authenticated=True, user=user, status="active", message="Session created.")


@router.get("/session", response_model=SessionResponse)
async def session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> SessionResponse:
    if not session_cookie:
        return SessionResponse(authenticated=False, user=None, status="inactive")
    payload = decode_session_token(session_cookie)
    if payload is None:
        return SessionResponse(authenticated=False, user=None, status="inactive")
    user = SessionUser(email=payload["email"], name=payload["name"], role=payload["role"])
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    return SessionResponse(authenticated=True, user=user, status="active", expiresAt=expires_at)


@router.post("/logout")
async def logout(response: Response, session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    payload = decode_session_token(session_cookie) if session_cookie else None
    if payload is not None:
        await write_audit_log(payload["email"], "auth", payload["email"], "logout", after={"email": payload["email"]})
    return {"status": "logged_out"}
