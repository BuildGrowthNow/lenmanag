from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.core.sites import site_repository
from app.schemas.message import (
    MessageCopyResponse,
    MessageDraft,
    MessageDraftCreateRequest,
    MessageDraftListResponse,
    MessageDraftPatchRequest,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRepository:
    def __init__(self) -> None:
        self._memory_ready = False
        self._memory: dict[str, dict[str, Any]] = {}

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None or self._memory_ready:
            return
        await database["message_drafts"].create_index([("leadId", 1), ("createdAt", -1)])
        await database["message_drafts"].create_index([("siteId", 1), ("createdAt", -1)])
        self._memory_ready = True

    async def _message_docs(self, lead_id: str) -> list[dict[str, Any]]:
        database = get_database()
        if database is None:
            return [dict(item) for item in self._memory.values() if item.get("leadId") == lead_id]
        cursor = database["message_drafts"].find({"leadId": lead_id}).sort("createdAt", -1)
        docs = await cursor.to_list(length=100)
        return [dict(doc) for doc in docs]

    async def create_draft(self, lead_id: str, request: MessageDraftCreateRequest) -> MessageDraft | None:
        await self._maybe_ensure_indexes()
        lead = await lead_repository.get_lead(lead_id)
        brief = await lead_repository.get_brief(lead_id)
        if lead is None or brief is None or brief.approvalState != "approved":
            return None
        site = await site_repository.get_site(lead_id)
        tone = brief.toneProfile.value or "clear"
        angle = brief.conversionAngle.value or "Keep the outreach tied to the approved preview story."
        cta_primary = site.ctaStrategy.primary if site else None
        cta_secondary = site.ctaStrategy.secondary if site else None
        calendly_url = cta_primary.href if cta_primary and "calendly" in cta_primary.href.lower() else None
        if calendly_url is None and cta_secondary and "calendly" in cta_secondary.href.lower():
            calendly_url = cta_secondary.href
        subject = f"{lead.companyName or 'Your site'} preview and next step"
        body = "\n".join(
            [
                f"Hi {lead.companyName or 'there'},",
                "",
                f"I reviewed the approved preview for {lead.companyName or lead.websiteUrl}.",
                f"The story centers on: {angle}",
                f"Preview: {site.previewUrl if site else f'/sites/{lead_id}'}",
                f"Primary CTA: {cta_primary.label if cta_primary else 'Review the preview'} -> {cta_primary.href if cta_primary else '#contact'}",
                f"Secondary CTA: {cta_secondary.label if cta_secondary else 'See source notes'} -> {cta_secondary.href if cta_secondary else '#source-notes'}",
                f"Calendly: {calendly_url or 'not captured in source data'}",
                "",
                "Would you like to review it and decide on a next step?",
            ]
        )
        now = _now()
        draft = MessageDraft(
            id=uuid4().hex,
            leadId=lead_id,
            briefId=brief.id,
            siteId=site.id if site else None,
            channel=request.channel,
            subject=subject,
            body=body,
            tone=tone,
            angle=angle,
            ctaPrimaryLabel=cta_primary.label if cta_primary else "Review the preview",
            ctaPrimaryHref=cta_primary.href if cta_primary else "#contact",
            ctaSecondaryLabel=cta_secondary.label if cta_secondary else "See source notes",
            ctaSecondaryHref=cta_secondary.href if cta_secondary else "#source-notes",
            calendlyUrl=calendly_url,
            previewUrl=site.previewUrl if site else None,
            exportUrl=site.exportMetadata.exportPath if site and site.exportMetadata else None,
            status="draft",
            version=1,
            createdAt=now,
            updatedAt=now,
        )
        database = get_database()
        if database is None:
            self._memory[draft.id] = draft.model_dump()
            return draft
        await database["message_drafts"].insert_one(draft.model_dump())
        return draft

    async def list_drafts(self, lead_id: str) -> MessageDraftListResponse:
        docs = await self._message_docs(lead_id)
        items = [MessageDraft.model_validate(doc) for doc in docs]
        return MessageDraftListResponse(leadId=lead_id, items=items)

    async def update_draft(self, draft_id: str, request: MessageDraftPatchRequest) -> MessageDraft | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        doc: dict[str, Any] | None = None
        if database is None:
            doc = self._memory.get(draft_id)
            if doc is None:
                return None
            updated = dict(doc)
        else:
            doc = await database["message_drafts"].find_one({"id": draft_id})
            if doc is None:
                return None
            updated = dict(doc)
        if request.subject is not None:
            updated["subject"] = request.subject.strip()
        if request.body is not None:
            updated["body"] = request.body.strip()
        if request.tone is not None:
            updated["tone"] = request.tone.strip()
        if request.angle is not None:
            updated["angle"] = request.angle.strip()
        content_changed = any(
            value is not None
            for value in (request.subject, request.body, request.tone, request.angle)
        )
        if request.status is not None:
            updated["status"] = request.status
        elif content_changed and updated.get("status") == "draft":
            updated["status"] = "edited"
        updated["version"] = int(updated.get("version", 1)) + 1
        updated["updatedAt"] = _now()
        if database is None:
            self._memory[draft_id] = updated
        else:
            await database["message_drafts"].update_one({"id": draft_id}, {"$set": updated})
        return MessageDraft.model_validate(updated)

    async def mark_ready(self, draft_id: str) -> MessageDraft | None:
        return await self.update_draft(draft_id, MessageDraftPatchRequest(status="ready"))

    async def get_copy(self, draft_id: str, channel: str | None = None) -> MessageCopyResponse | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            doc = self._memory.get(draft_id)
        else:
            doc = await database["message_drafts"].find_one({"id": draft_id})
        if doc is None:
            return None
        draft = MessageDraft.model_validate(doc)
        copy_channel = channel or draft.channel
        return MessageCopyResponse(
            id=draft.id,
            channel=copy_channel,
            subject=draft.subject,
            body=draft.body,
            ctaPrimaryLabel=draft.ctaPrimaryLabel,
            ctaPrimaryHref=draft.ctaPrimaryHref,
            ctaSecondaryLabel=draft.ctaSecondaryLabel,
            ctaSecondaryHref=draft.ctaSecondaryHref,
            calendlyUrl=draft.calendlyUrl,
            previewUrl=draft.previewUrl,
            exportUrl=draft.exportUrl,
            status=draft.status,
            updatedAt=draft.updatedAt,
        )


message_repository = MessageRepository()
