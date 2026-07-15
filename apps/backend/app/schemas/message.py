from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

MessageStatus = Literal["draft", "edited", "ready", "sent", "failed"]
DeliveryChannel = Literal["whatsapp", "linkedin", "email", "generic"]


class MessageDraft(BaseModel):
    id: str
    leadId: str
    briefId: str
    siteId: Optional[str] = None
    channel: str
    deliveryChannel: DeliveryChannel = "email"
    subject: str
    body: str
    tone: str
    tonePreset: Optional[str] = None
    customTone: Optional[str] = None
    angle: str
    ctaVariant: Optional[str] = None
    ctaPosition: Optional[str] = None
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

    @field_validator("calendlyUrl")
    @classmethod
    def validate_calendly_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if "calendly" not in parsed.netloc.lower():
                raise ValueError("URL must be a Calendly link")
            return v
        except Exception as e:
            raise ValueError(f"Invalid Calendly URL: {e}")


class MessageDraftCreateRequest(BaseModel):
    channel: str = "email"


class MessageDraftPatchRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    tone: Optional[str] = None
    tonePreset: Optional[str] = None
    customTone: Optional[str] = None
    angle: Optional[str] = None
    ctaVariant: Optional[str] = None
    ctaPosition: Optional[str] = None
    deliveryChannel: Optional[DeliveryChannel] = None
    status: Optional[MessageStatus] = None


class MessageDraftListResponse(BaseModel):
    leadId: str
    items: list[MessageDraft] = Field(default_factory=list)


class TonePreset(BaseModel):
    id: str
    name: str
    description: str
    example: str


class CtaVariant(BaseModel):
    id: str
    name: str
    description: str
    label: str
    position: str


class PreviewContextResponse(BaseModel):
    draftId: str
    leadId: str
    briefSummary: str | None
    sitePreviewUrl: str | None
    sitePreviewSlug: str | None
    ctaPrimaryLabel: str | None
    ctaPrimaryHref: str | None
    ctaSecondaryLabel: str | None
    ctaSecondaryHref: str | None
    calendlyUrl: str | None
    exportUrl: str | None


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
