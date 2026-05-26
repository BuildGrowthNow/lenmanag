from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

MessageStatus = Literal["draft", "edited", "ready"]


class MessageDraft(BaseModel):
    id: str
    leadId: str
    briefId: str
    siteId: Optional[str] = None
    channel: str
    subject: str
    body: str
    tone: str
    angle: str
    ctaPrimaryLabel: Optional[str] = None
    ctaPrimaryHref: Optional[str] = None
    ctaSecondaryLabel: Optional[str] = None
    ctaSecondaryHref: Optional[str] = None
    calendlyUrl: Optional[str] = None
    previewUrl: Optional[str] = None
    exportUrl: Optional[str] = None
    status: MessageStatus = "draft"
    version: int
    createdAt: datetime
    updatedAt: datetime


class MessageDraftCreateRequest(BaseModel):
    channel: str = "email"


class MessageDraftPatchRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    tone: Optional[str] = None
    angle: Optional[str] = None
    status: Optional[MessageStatus] = None


class MessageDraftListResponse(BaseModel):
    leadId: str
    items: list[MessageDraft] = Field(default_factory=list)


class MessageCopyResponse(BaseModel):
    id: str
    channel: str
    subject: str
    body: str
    ctaPrimaryLabel: Optional[str] = None
    ctaPrimaryHref: Optional[str] = None
    ctaSecondaryLabel: Optional[str] = None
    ctaSecondaryHref: Optional[str] = None
    calendlyUrl: Optional[str] = None
    previewUrl: Optional[str] = None
    exportUrl: Optional[str] = None
    status: MessageStatus
    updatedAt: datetime
