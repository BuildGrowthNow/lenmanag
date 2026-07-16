from __future__ import annotations

import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.rate_limiter import check_auth_rate_limit
from app.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
    decode_session_token,
)
from app.core.versioning import response_meta
from app.schemas.auth import (
    AuthDecisionResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionResponse,
    SessionUser,
    VerificationRequest,
)
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        max_age=settings.session_cookie_max_age_seconds,
        path="/",
    )


def _delete_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=settings.session_cookie_domain,
    )


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


@router.post("/verify", response_model=ResponseEnvelope[AuthDecisionResponse])
async def verify_login(
    payload: VerificationRequest, request: Request
) -> ResponseEnvelope[AuthDecisionResponse]:
    check_auth_rate_limit(request, "auth:verify")
    allowed, reason = _is_allowlisted(payload.email)
    await write_audit_log(
        None,
        "auth",
        _normalize_email(str(payload.email)),
        "verify_login",
        after={"allowed": allowed, "reason": reason},
    )
    return success_response(
        AuthDecisionResponse(allowed=allowed, reason=reason, email=payload.email),
        meta=response_meta(request),
    )


def _check_password(provided: str) -> bool:
    expected = settings.auth_admin_password
    if not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


@router.post("/login", response_model=ResponseEnvelope[LoginResponse])
async def login(
    payload: LoginRequest, response: Response, request: Request
) -> ResponseEnvelope[LoginResponse]:
    check_auth_rate_limit(request, "auth:login")
    email = _normalize_email(str(payload.email))
    allowed, reason = _is_allowlisted(payload.email)

    # Check both conditions — give the same generic error either way to avoid
    # leaking whether the email is on the allowlist or the password is wrong.
    if not allowed or not _check_password(payload.password):
        await write_audit_log(
            None,
            "auth",
            email,
            "login_denied",
            after={"reason": reason or "bad_password"},
        )
        denied_response = LoginResponse(
            authenticated=False,
            user=None,
            status="denied",
            message="Access denied. Check your email and password.",
        )
        return success_response(denied_response, meta=response_meta(request))

    name = email.split("@", 1)[0]
    token = create_session_token(email=email, name=name)
    _set_session_cookie(response, token)
    user = SessionUser(email=email, name=name, role="operator")
    await write_audit_log(email, "auth", email, "login_success", after={"email": email})
    return success_response(
        LoginResponse(
            authenticated=True, user=user, status="active", message="Session created."
        ),
        meta=response_meta(request),
    )


@router.get("/session", response_model=ResponseEnvelope[SessionResponse])
async def session(
    request: Request,
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> ResponseEnvelope[SessionResponse]:
    if not session_cookie:
        inactive_response = SessionResponse(
            authenticated=False, user=None, status="inactive"
        )
        return success_response(inactive_response, meta=response_meta(request))
    token_payload = decode_session_token(session_cookie)
    if token_payload is None:
        inactive_response = SessionResponse(
            authenticated=False, user=None, status="inactive"
        )
        return success_response(inactive_response, meta=response_meta(request))
    user = SessionUser(
        email=token_payload["email"],
        name=token_payload["name"],
        role=token_payload["role"],
    )
    expires_at = datetime.fromtimestamp(token_payload["exp"], tz=timezone.utc)
    return success_response(
        SessionResponse(
            authenticated=True, user=user, status="active", expiresAt=expires_at
        ),
        meta=response_meta(request),
    )


@router.post("/refresh", response_model=ResponseEnvelope[SessionResponse])
async def refresh_session(
    request: Request,
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> ResponseEnvelope[SessionResponse]:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = create_session_token(
        email=payload["email"],
        name=payload.get("name"),
        role=payload.get("role", "operator"),
    )
    _set_session_cookie(response, token)
    refreshed_payload = decode_session_token(token)
    expires_at = None
    if refreshed_payload and refreshed_payload.get("exp"):
        expires_at = datetime.fromtimestamp(refreshed_payload["exp"], tz=timezone.utc)
    user = SessionUser(
        email=payload["email"],
        name=payload.get("name") or payload["email"].split("@")[0],
        role=payload.get("role", "operator"),
    )
    return success_response(
        SessionResponse(
            authenticated=True, user=user, status="active", expiresAt=expires_at
        ),
        meta=response_meta(request),
    )


@router.post("/logout", response_model=ResponseEnvelope[LogoutResponse])
async def logout(
    request: Request,
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> ResponseEnvelope[LogoutResponse]:
    _delete_session_cookie(response)
    payload = decode_session_token(session_cookie) if session_cookie else None
    if payload is not None:
        await write_audit_log(
            payload["email"],
            "auth",
            payload["email"],
            "logout",
            after={"email": payload["email"]},
        )
    return success_response(
        LogoutResponse(status="logged_out"), meta=response_meta(request)
    )
