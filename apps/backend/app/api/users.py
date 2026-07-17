from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from app.core.audit import write_audit_log
from app.core.auth_dependencies import CurrentUser
from app.core.config import get_settings
from app.core.email_service import send_password_reset_email, send_verification_email
from app.core.jwt_handler import create_access_token
from app.core.rate_limiter import check_auth_rate_limit
from app.core.users import UserRepository
from app.core.versioning import response_meta
from app.schemas.response import ResponseEnvelope, success_response
from app.schemas.user import (
    ForgotPasswordRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _user_to_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        is_verified=user.get("is_verified", False),
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )


@router.post("/signup", response_model=ResponseEnvelope[TokenResponse])
async def signup(
    payload: UserCreate, request: Request
) -> ResponseEnvelope[TokenResponse]:
    check_auth_rate_limit(request, "users:signup")

    if settings.signup_code and payload.signup_code != settings.signup_code:
        raise HTTPException(status_code=403, detail="Invalid signup code")

    repo = UserRepository()
    await repo.ensure_indexes()

    try:
        user = await repo.create_user(email=payload.email, password=payload.password)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")

    verification_token = user.get("verification_token")

    if verification_token:
        await send_verification_email(
            email=user["email"],
            verification_token=verification_token,
        )

    access_token = create_access_token(user_id=str(user["_id"]), email=user["email"])
    user_response = _user_to_response(user)

    await write_audit_log(
        user["email"],
        "auth",
        user["email"],
        "signup",
        after={"user_id": str(user["_id"])},
    )

    return success_response(
        TokenResponse(access_token=access_token, user=user_response),
        meta=response_meta(request),
    )


@router.post("/login", response_model=ResponseEnvelope[TokenResponse])
async def login_user(
    payload: UserLogin, request: Request
) -> ResponseEnvelope[TokenResponse]:
    check_auth_rate_limit(request, "users:login")

    repo = UserRepository()
    user = await repo.verify_password(email=payload.email, password=payload.password)

    if not user:
        await write_audit_log(
            None,
            "auth",
            payload.email,
            "login_failed",
            after={"reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user_id=str(user["_id"]), email=user["email"])
    user_response = _user_to_response(user)

    await write_audit_log(
        user["email"],
        "auth",
        user["email"],
        "login",
        after={"user_id": str(user["_id"])},
    )

    return success_response(
        TokenResponse(access_token=access_token, user=user_response),
        meta=response_meta(request),
    )


@router.post("/verify-email", response_model=ResponseEnvelope[dict])
async def verify_email(
    payload: VerifyEmailRequest, request: Request
) -> ResponseEnvelope[dict]:
    repo = UserRepository()
    user = await repo.verify_email(token=payload.token)

    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )

    await write_audit_log(
        user["email"],
        "auth",
        user["email"],
        "email_verified",
        after={"user_id": str(user["_id"])},
    )

    return success_response(
        {"message": "Email verified successfully", "email": user["email"]},
        meta=response_meta(request),
    )


@router.post("/resend-verification", response_model=ResponseEnvelope[dict])
async def resend_verification(
    payload: ResendVerificationRequest, request: Request
) -> ResponseEnvelope[dict]:
    check_auth_rate_limit(request, "users:resend-verification")

    repo = UserRepository()
    user = await repo.get_user_by_email(payload.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")

    verification_token = await repo.update_verification_token(payload.email)

    if verification_token:
        await send_verification_email(
            email=user["email"],
            verification_token=verification_token,
        )

    return success_response(
        {"message": "Verification email sent"}, meta=response_meta(request)
    )


@router.post("/forgot-password", response_model=ResponseEnvelope[dict])
async def forgot_password(
    payload: ForgotPasswordRequest, request: Request
) -> ResponseEnvelope[dict]:
    check_auth_rate_limit(request, "users:forgot-password")

    repo = UserRepository()
    reset_token = await repo.create_password_reset_token(payload.email)

    if reset_token:
        await send_password_reset_email(
            email=payload.email,
            reset_token=reset_token,
        )

        await write_audit_log(
            payload.email,
            "auth",
            payload.email,
            "password_reset_requested",
            after={},
        )

    return success_response(
        {"message": "If the email exists, a password reset link has been sent"},
        meta=response_meta(request),
    )


@router.post("/reset-password", response_model=ResponseEnvelope[dict])
async def reset_password(
    payload: ResetPasswordRequest, request: Request
) -> ResponseEnvelope[dict]:
    check_auth_rate_limit(request, "users:reset-password")

    repo = UserRepository()
    user = await repo.reset_password(token=payload.token, new_password=payload.new_password)

    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid or expired password reset token"
        )

    await write_audit_log(
        user["email"],
        "auth",
        user["email"],
        "password_reset_completed",
        after={"user_id": str(user["_id"])},
    )

    return success_response(
        {"message": "Password reset successfully"},
        meta=response_meta(request),
    )


@router.get("/me", response_model=ResponseEnvelope[UserResponse])
async def get_current_user_info(
    user: CurrentUser, request: Request
) -> ResponseEnvelope[UserResponse]:
    return success_response(_user_to_response(user), meta=response_meta(request))
