from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class VerificationRequest(BaseModel):
    email: EmailStr


class SessionUser(BaseModel):
    email: EmailStr
    name: str
    role: Literal["operator", "admin"]


class SessionResponse(BaseModel):
    authenticated: bool
    user: Optional[SessionUser] = None
    status: Literal["active", "inactive"]
    expiresAt: Optional[datetime] = None


class AuthDecisionResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    email: EmailStr


class LoginResponse(BaseModel):
    authenticated: bool
    user: Optional[SessionUser] = None
    status: Literal["active", "denied"]
    message: str


class LogoutResponse(BaseModel):
    status: Literal["logged_out"]

