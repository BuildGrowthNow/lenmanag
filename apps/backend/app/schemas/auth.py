from typing import Optional

from pydantic import BaseModel, EmailStr


class VerificationRequest(BaseModel):
    email: EmailStr


class AuthDecisionResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    email: EmailStr
