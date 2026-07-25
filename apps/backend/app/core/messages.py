from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.analytics import analytics_repository
from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.core.sites import site_repository
from app.schemas.message import (
    CtaVariant,
    GeneratedMessageVariant,
    MessageCopyResponse,
    MessageDraft,
    MessageDraftCreateRequest,
    MessageDraftListResponse,
    MessageDraftPatchRequest,
    TonePreset,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_tone_presets() -> list[TonePreset]:
    return [
        TonePreset(
            id="professional",
            name="Professional",
            description="Formal and business-focused tone",
            example="I hope this message finds you well. I would like to discuss...",
        ),
        TonePreset(
            id="casual",
            name="Casual",
            description="Relaxed and conversational tone",
            example="Hey! Just wanted to reach out about...",
        ),
        TonePreset(
            id="urgent",
            name="Urgent",
            description="Time-sensitive and action-oriented tone",
            example="Quick update - time is of the essence for...",
        ),
        TonePreset(
            id="friendly",
            name="Friendly",
            description="Warm and approachable tone",
            example="Hi there! I'm excited to share with you...",
        ),
    ]


def get_cta_variants() -> list[CtaVariant]:
    return [
        CtaVariant(
            id="primary",
            name="Primary CTA",
            description="Main call-to-action for the message",
            label="Review the preview",
            position="bottom",
        ),
        CtaVariant(
            id="secondary",
            name="Secondary CTA",
            description="Alternative call-to-action",
            label="See source notes",
            position="bottom",
        ),
        CtaVariant(
            id="tertiary",
            name="Tertiary CTA",
            description="Additional call-to-action option",
            label="Learn more",
            position="inline",
        ),
    ]


def get_channel_config(channel: str) -> dict[str, Any]:
    configs: dict[str, dict[str, Any]] = {
        "whatsapp": {
            "characterLimit": 1000,
            "formatting": "plain",
            "supportsHtml": False,
            "supportsLinks": True,
            "description": "WhatsApp message format",
        },
        "linkedin": {
            "characterLimit": 3000,
            "formatting": "markdown",
            "supportsHtml": False,
            "supportsLinks": True,
            "description": "LinkedIn message format",
        },
        "email": {
            "characterLimit": 10000,
            "formatting": "html",
            "supportsHtml": True,
            "supportsLinks": True,
            "description": "Email format",
        },
        "generic": {
            "characterLimit": 5000,
            "formatting": "plain",
            "supportsHtml": False,
            "supportsLinks": True,
            "description": "Generic message format",
        },
    }
    return configs.get(channel, configs["generic"])


class MessageRepository:
    def __init__(self) -> None:
        self._memory_ready = False
        self._memory: dict[str, dict[str, Any]] = {}

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None or self._memory_ready:
            return
        await database["message_drafts"].create_index(
            [("leadId", 1), ("createdAt", -1)]
        )
        await database["message_drafts"].create_index(
            [("siteId", 1), ("createdAt", -1)]
        )
        self._memory_ready = True

    async def _message_docs(self, lead_id: str) -> list[dict[str, Any]]:
        database = get_database()
        if database is None:
            return [
                dict(item)
                for item in self._memory.values()
                if item.get("leadId") == lead_id
            ]
        cursor = (
            database["message_drafts"].find({"leadId": lead_id}).sort("createdAt", -1)
        )
        docs = await cursor.to_list(length=100)
        return [dict(doc) for doc in docs]

    async def _ai_generate_variant(
        self,
        channel: str,
        company_name: str,
        preview_url: str,
        compare_url: str,
        value_proposition: str,
        conversion_action: str,
        primary_audience: str,
        tone_and_voice: str,
        pain_points: list[str],
        section_headlines: list[str],
        cta_label: str,
    ) -> GeneratedMessageVariant:
        """Generate a single channel-specific outbound message using the LLM."""
        from app.core.llm import get_llm_client

        channel_instructions = {
            "email": (
                "Write a cold outbound email. Include a subject line (prefix it with 'Subject: ')."
                " Keep the body under 120 words. Personalize the opening with a specific observation"
                " about their business. Mention one concrete pain point. Include the preview link"
                " naturally near the end. Avoid salesy language — sound like a thoughtful peer."
                " Sign off with a soft call-to-action asking for a quick reaction, not a meeting."
            ),
            "linkedin": (
                "Write a LinkedIn connection note. Max 300 characters total."
                " Sound human, not pitchy. Reference something specific about what they do."
                " End with a single question or light hook. No links — just the connection message."
            ),
            "whatsapp": (
                "Write a short WhatsApp follow-up (assume you've already connected)."
                " Under 80 words. Casual and direct. Reference the preview link."
                " Single paragraph. End with an open question or next step prompt."
            ),
        }
        instruction = channel_instructions.get(channel, channel_instructions["email"])

        pain_points_str = (
            "\n".join(f"- {p}" for p in pain_points[:3])
            if pain_points
            else "Not specified"
        )
        headlines_str = (
            ", ".join(f'"{h}"' for h in section_headlines[:4])
            if section_headlines
            else "Not specified"
        )

        prompt = f"""You are writing outbound sales messages for a B2B agency that builds custom landing page previews for prospective clients.

COMPANY: {company_name}
VALUE PROPOSITION: {value_proposition}
TARGET AUDIENCE: {primary_audience}
CONVERSION GOAL: {conversion_action}
TONE & VOICE: {tone_and_voice}
PAIN POINTS ADDRESSED: {pain_points_str}
PAGE SECTION HEADLINES: {headlines_str}
PREVIEW LINK: {preview_url}
COMPARE ALL VARIANTS LINK: {compare_url}
PRIMARY CTA: {cta_label}

CHANNEL: {channel.upper()}
INSTRUCTION: {instruction}

Return ONLY a valid JSON object with these fields:
{{
  "subject": "email subject line (empty string for non-email channels)",
  "body": "the message body",
  "angle": "one sentence describing the persuasion angle used"
}}

Write the message now. Be specific, not generic. Reference their actual business context."""

        llm = get_llm_client()
        try:
            raw = await llm.generate_text(prompt, temperature=0.7, max_tokens=600)
            parsed = llm.extract_json_from_response(raw)
            subject = str(parsed.get("subject", "")).strip()
            if subject.lower().startswith("subject:"):
                subject = subject[8:].strip()
            return GeneratedMessageVariant(
                channel=channel
                if channel in ("email", "linkedin", "whatsapp", "generic")
                else "email",  # type: ignore[arg-type]
                subject=subject,
                body=str(parsed.get("body", "")).strip(),
                angle=str(parsed.get("angle", conversion_action)).strip(),
            )
        except Exception as exc:
            logger.warning(
                "AI message generation failed for channel %s: %s", channel, exc
            )
            fallback_body = (
                f"Hi {company_name},\n\n"
                f"I built a custom landing page preview for your business.\n\n"
                f"It focuses on: {conversion_action}\n\n"
                f"Take a look: {preview_url}\n\n"
                f"Would love your reaction."
            )
            return GeneratedMessageVariant(
                channel=channel
                if channel in ("email", "linkedin", "whatsapp", "generic")
                else "email",  # type: ignore[arg-type]
                subject=f"{company_name} — custom preview",
                body=fallback_body,
                angle=conversion_action,
            )

    async def create_draft(
        self, lead_id: str, request: MessageDraftCreateRequest, user_id: str = ""
    ) -> MessageDraft | None:
        await self._maybe_ensure_indexes()
        lead = await lead_repository.get_lead(lead_id)
        brief = await lead_repository.get_master_brief(lead_id)
        if lead is None or brief is None or brief.approvalState != "approved":
            return None
        site = await site_repository.get_site(lead_id)

        channel = (
            request.channel
            if request.channel in ("whatsapp", "linkedin", "email", "generic")
            else "email"
        )
        delivery_channel: Any = channel

        cta_primary = site.ctaStrategy.primary if site else None
        cta_secondary = site.ctaStrategy.secondary if site else None
        calendly_url = (
            cta_primary.href
            if cta_primary and "calendly" in cta_primary.href.lower()
            else None
        )
        if (
            calendly_url is None
            and cta_secondary
            and "calendly" in cta_secondary.href.lower()
        ):
            calendly_url = cta_secondary.href

        preview_url = site.previewUrl if site else f"/st/{lead_id}"
        company_name = lead.companyName or lead.websiteUrl or "your company"

        from app.core.config import get_settings

        settings = get_settings()
        app_base = (settings.preview_base_url or "https://sites.lenquant.com").rstrip(
            "/"
        )
        compare_url = f"{app_base}/compare/{lead_id}"

        pain_points: list[str] = []
        if brief.extractedContent:
            pain_points = list(brief.extractedContent.get("pain_points", []))[:3]
        if not pain_points and brief.primaryAudience:
            pain_points = [f"Challenges faced by {brief.primaryAudience}"]

        section_headlines = [s.headline for s in (brief.sections or []) if s.headline]

        cta_label = (
            cta_primary.label
            if cta_primary
            else brief.conversionAction or "Review the preview"
        )

        variant = await self._ai_generate_variant(
            channel=channel,
            company_name=company_name,
            preview_url=preview_url,
            compare_url=compare_url,
            value_proposition=brief.valueProposition,
            conversion_action=brief.conversionAction,
            primary_audience=brief.primaryAudience,
            tone_and_voice=brief.toneAndVoice,
            pain_points=pain_points,
            section_headlines=section_headlines,
            cta_label=cta_label,
        )

        now = _now()
        draft = MessageDraft(
            id=uuid4().hex,
            user_id=user_id,
            leadId=lead_id,
            briefId=brief.id,
            siteId=site.id if site else None,
            channel=channel,
            deliveryChannel=delivery_channel,
            subject=variant.subject,
            body=variant.body,
            tone=brief.toneAndVoice or "clear",
            tonePreset=None,
            customTone=None,
            angle=variant.angle,
            ctaVariant=None,
            ctaPosition=None,
            ctaPrimaryLabel=cta_primary.label if cta_primary else "Review the preview",
            ctaPrimaryHref=cta_primary.href if cta_primary else preview_url,
            ctaSecondaryLabel=cta_secondary.label
            if cta_secondary
            else "See source notes",
            ctaSecondaryHref=cta_secondary.href if cta_secondary else "#source-notes",
            calendlyUrl=calendly_url,
            previewUrl=preview_url,
            compareUrl=compare_url,
            exportUrl=site.exportMetadata.exportPath
            if site and site.exportMetadata
            else None,
            status="draft",
            version=1,
            createdAt=now,
            updatedAt=now,
        )
        database = get_database()
        if database is None:
            self._memory[draft.id] = draft.model_dump()
        else:
            await database["message_drafts"].insert_one(draft.model_dump())
        await analytics_repository.record_admin_event(
            event_type="message_draft_created",
            event_name=f"Message draft created ({draft.channel})",
            lead_id=lead_id,
            site_id=draft.siteId,
            metadata={"channel": draft.channel},
        )
        return draft

    async def bulk_generate_drafts(
        self, lead_id: str, user_id: str = "", force: bool = False
    ) -> list[MessageDraft]:
        """Generate one draft per channel (email, linkedin, whatsapp) in sequence."""
        await self._maybe_ensure_indexes()
        lead = await lead_repository.get_lead(lead_id)
        brief = await lead_repository.get_master_brief(lead_id)
        if lead is None or brief is None or brief.approvalState != "approved":
            return []

        existing = await self._message_docs(lead_id)
        existing_channels = {doc.get("channel") for doc in existing}

        channels_to_generate = ["email", "linkedin", "whatsapp"]
        if not force:
            channels_to_generate = [
                c for c in channels_to_generate if c not in existing_channels
            ]
        if not channels_to_generate:
            return [MessageDraft.model_validate(doc) for doc in existing]

        created: list[MessageDraft] = []
        for channel in channels_to_generate:
            draft = await self.create_draft(
                lead_id,
                MessageDraftCreateRequest(channel=channel),
                user_id=user_id,
            )
            if draft is not None:
                created.append(draft)

        return created

    async def list_drafts(self, lead_id: str) -> MessageDraftListResponse:
        docs = await self._message_docs(lead_id)
        items = [MessageDraft.model_validate(doc) for doc in docs]
        return MessageDraftListResponse(leadId=lead_id, items=items)

    async def update_draft(
        self, draft_id: str, request: MessageDraftPatchRequest
    ) -> MessageDraft | None:
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
        if request.tonePreset is not None:
            updated["tonePreset"] = request.tonePreset
        if request.customTone is not None:
            updated["customTone"] = request.customTone.strip()
        if request.angle is not None:
            updated["angle"] = request.angle.strip()
        if request.ctaVariant is not None:
            updated["ctaVariant"] = request.ctaVariant
        if request.ctaPosition is not None:
            updated["ctaPosition"] = request.ctaPosition
        if request.deliveryChannel is not None:
            updated["deliveryChannel"] = request.deliveryChannel
        if "calendlyUrl" in request.model_fields_set:
            updated["calendlyUrl"] = request.calendlyUrl
        content_changed = any(
            value is not None
            for value in (
                request.subject,
                request.body,
                request.tone,
                request.angle,
                request.tonePreset,
                request.customTone,
                request.ctaVariant,
                request.ctaPosition,
            )
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
            await database["message_drafts"].update_one(
                {"id": draft_id}, {"$set": updated}
            )
        snapshot = MessageDraft.model_validate(updated)
        if (
            request.subject is not None
            or request.body is not None
            or request.tone is not None
            or request.angle is not None
            or request.status is not None
        ):
            await analytics_repository.record_admin_event(
                event_type="message_draft_edited",
                event_name="Message draft updated",
                lead_id=snapshot.leadId,
                site_id=snapshot.siteId,
                metadata={"channel": snapshot.channel, "status": snapshot.status},
            )
        return snapshot

    async def mark_ready(self, draft_id: str) -> MessageDraft | None:
        is_valid, errors = await self.validate_ready_status(draft_id)
        if not is_valid:
            raise ValueError(f"Cannot mark as ready: {', '.join(errors)}")
        draft = await self.update_draft(
            draft_id, MessageDraftPatchRequest(status="ready")
        )
        if draft is not None:
            await analytics_repository.record_admin_event(
                event_type="message_marked_ready",
                event_name="Message draft marked ready",
                lead_id=draft.leadId,
                site_id=draft.siteId,
                metadata={"channel": draft.channel},
            )
        return draft

    async def mark_sent(self, draft_id: str) -> MessageDraft | None:
        database = get_database()
        if database is None:
            doc = self._memory.get(draft_id)
        else:
            doc = await database["message_drafts"].find_one({"id": draft_id})
        if doc is None:
            return None
        draft = MessageDraft.model_validate(doc)
        if draft.status != "ready":
            raise ValueError("Can only mark sent messages as ready")
        draft = await self.update_draft(
            draft_id, MessageDraftPatchRequest(status="sent")
        )
        if draft is not None:
            await analytics_repository.record_admin_event(
                event_type="message_marked_sent",
                event_name="Message draft marked sent",
                lead_id=draft.leadId,
                site_id=draft.siteId,
                metadata={"channel": draft.channel},
            )
        return draft

    async def reset_to_draft(self, draft_id: str) -> MessageDraft | None:
        draft = await self.update_draft(
            draft_id, MessageDraftPatchRequest(status="draft")
        )
        if draft is not None:
            await analytics_repository.record_admin_event(
                event_type="message_reset_to_draft",
                event_name="Message draft reset to draft",
                lead_id=draft.leadId,
                site_id=draft.siteId,
                metadata={"channel": draft.channel},
            )
        return draft

    async def validate_ready_status(self, draft_id: str) -> tuple[bool, list[str]]:
        database = get_database()
        if database is None:
            doc = self._memory.get(draft_id)
        else:
            doc = await database["message_drafts"].find_one({"id": draft_id})
        if doc is None:
            return False, ["Draft not found"]
        draft = MessageDraft.model_validate(doc)
        errors = []
        if not draft.subject or not draft.subject.strip():
            errors.append("Subject is required")
        if not draft.body or not draft.body.strip():
            errors.append("Body is required")
        if not draft.ctaPrimaryHref:
            errors.append("Primary CTA link is required")
        return len(errors) == 0, errors

    async def get_preview_context(self, draft_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            doc = self._memory.get(draft_id)
        else:
            doc = await database["message_drafts"].find_one({"id": draft_id})
        if doc is None:
            return None
        draft = MessageDraft.model_validate(doc)
        brief = await lead_repository.get_master_brief(draft.leadId)
        site = await site_repository.get_site(draft.leadId)
        return {
            "draftId": draft.id,
            "leadId": draft.leadId,
            "briefSummary": brief.valueProposition if brief else None,
            "sitePreviewUrl": site.previewUrl if site else None,
            "sitePreviewSlug": site.previewSlug if site else None,
            "ctaPrimaryLabel": draft.ctaPrimaryLabel,
            "ctaPrimaryHref": draft.ctaPrimaryHref,
            "ctaSecondaryLabel": draft.ctaSecondaryLabel,
            "ctaSecondaryHref": draft.ctaSecondaryHref,
            "calendlyUrl": draft.calendlyUrl,
            "exportUrl": draft.exportUrl,
        }

    async def get_copy(
        self, draft_id: str, channel: str | None = None
    ) -> MessageCopyResponse | None:
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
