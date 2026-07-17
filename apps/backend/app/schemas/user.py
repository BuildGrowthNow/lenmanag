import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
        raise ValueError("Password must contain at least one special character")
    return password


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    signup_code: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    is_verified: Optional[bool] = None


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)
