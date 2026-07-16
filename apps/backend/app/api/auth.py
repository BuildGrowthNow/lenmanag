from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.rate_limiter import check_auth_rate_limit
from app.core.versioning import response_meta
from app.schemas.auth import AuthDecisionResponse, VerificationRequest
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


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
