from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.audit import write_audit_log
from app.core.auth_dependencies import CurrentUserId
from app.core.messages import (
    get_channel_config,
    get_cta_variants,
    get_tone_presets,
    message_repository,
)
from app.core.versioning import response_meta
from app.schemas.message import (
    CtaVariant,
    MessageCopyResponse,
    MessageDraft,
    MessageDraftCreateRequest,
    MessageDraftListResponse,
    MessageDraftPatchRequest,
    PreviewContextResponse,
    TonePreset,
)
from app.schemas.response import ResponseEnvelope, success_response

router = APIRouter(tags=["messages"])


@router.post("/leads/{lead_id}/messages", response_model=ResponseEnvelope[MessageDraft])
async def create_message_draft(
    lead_id: str,
    payload: MessageDraftCreateRequest,
    http_request: Request,
    user_id: CurrentUserId,
) -> ResponseEnvelope[MessageDraft]:
    draft = await message_repository.create_draft(lead_id, payload)
    if draft is None:
        raise HTTPException(
            status_code=409, detail="Approve the brief before creating a message draft."
        )
    await write_audit_log(
        user_id,
        "message",
        draft.id,
        "message_draft_create",
        after=draft.model_dump(),
    )
    return success_response(draft, meta=response_meta(http_request))


@router.get(
    "/leads/{lead_id}/messages",
    response_model=ResponseEnvelope[MessageDraftListResponse],
)
async def list_message_drafts(
    lead_id: str, http_request: Request, _user_id: CurrentUserId
) -> ResponseEnvelope[MessageDraftListResponse]:
    return success_response(
        await message_repository.list_drafts(lead_id), meta=response_meta(http_request)
    )


@router.patch("/messages/{draft_id}", response_model=ResponseEnvelope[MessageDraft])
async def patch_message_draft(
    draft_id: str,
    payload: MessageDraftPatchRequest,
    http_request: Request,
    user_id: CurrentUserId,
) -> ResponseEnvelope[MessageDraft]:
    before = await message_repository.get_copy(draft_id)
    draft = await message_repository.update_draft(draft_id, payload)
    if draft is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(
        user_id,
        "message",
        draft.id,
        "message_draft_edit",
        before=before.model_dump() if before else None,
        after=draft.model_dump(),
    )
    return success_response(draft, meta=response_meta(http_request))


@router.post(
    "/messages/{draft_id}/ready", response_model=ResponseEnvelope[MessageDraft]
)
async def mark_message_ready(
    draft_id: str, http_request: Request, user_id: CurrentUserId
) -> ResponseEnvelope[MessageDraft]:
    before = await message_repository.get_copy(draft_id)
    draft = await message_repository.mark_ready(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(
        user_id,
        "message",
        draft.id,
        "message_marked_ready",
        before=before.model_dump() if before else None,
        after=draft.model_dump(),
    )
    return success_response(draft, meta=response_meta(http_request))


@router.get(
    "/messages/{draft_id}/copy", response_model=ResponseEnvelope[MessageCopyResponse]
)
async def copy_message_draft(
    draft_id: str,
    http_request: Request,
    user_id: CurrentUserId,
    channel: str | None = Query(default=None),
) -> ResponseEnvelope[MessageCopyResponse]:
    copy = await message_repository.get_copy(draft_id, channel=channel)
    if copy is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(
        user_id,
        "message",
        draft_id,
        "message_copy_requested",
        after={"channel": copy.channel, "status": copy.status},
    )
    return success_response(copy, meta=response_meta(http_request))


@router.get("/messages/tone-presets", response_model=ResponseEnvelope[list[TonePreset]])
async def get_tone_presets_endpoint(
    http_request: Request, _user_id: CurrentUserId
) -> ResponseEnvelope[list[TonePreset]]:
    return success_response(get_tone_presets(), meta=response_meta(http_request))


@router.get("/messages/cta-variants", response_model=ResponseEnvelope[list[CtaVariant]])
async def get_cta_variants_endpoint(
    http_request: Request, _user_id: CurrentUserId
) -> ResponseEnvelope[list[CtaVariant]]:
    return success_response(get_cta_variants(), meta=response_meta(http_request))


@router.get("/messages/channels/{channel}/config")
async def get_channel_config_endpoint(
    channel: str, http_request: Request, _user_id: CurrentUserId
) -> ResponseEnvelope[dict]:
    return success_response(
        get_channel_config(channel), meta=response_meta(http_request)
    )


@router.post(
    "/messages/{draft_id}/mark-sent", response_model=ResponseEnvelope[MessageDraft]
)
async def mark_message_sent(
    draft_id: str, http_request: Request, user_id: CurrentUserId
) -> ResponseEnvelope[MessageDraft]:
    before = await message_repository.get_copy(draft_id)
    draft = await message_repository.mark_sent(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(
        user_id,
        "message",
        draft.id,
        "message_marked_sent",
        before=before.model_dump() if before else None,
        after=draft.model_dump(),
    )
    return success_response(draft, meta=response_meta(http_request))


@router.post(
    "/messages/{draft_id}/reset-to-draft", response_model=ResponseEnvelope[MessageDraft]
)
async def reset_message_to_draft(
    draft_id: str, http_request: Request, user_id: CurrentUserId
) -> ResponseEnvelope[MessageDraft]:
    before = await message_repository.get_copy(draft_id)
    draft = await message_repository.reset_to_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(
        user_id,
        "message",
        draft.id,
        "message_reset_to_draft",
        before=before.model_dump() if before else None,
        after=draft.model_dump(),
    )
    return success_response(draft, meta=response_meta(http_request))


@router.get(
    "/messages/{draft_id}/preview-context",
    response_model=ResponseEnvelope[PreviewContextResponse],
)
async def get_preview_context(
    draft_id: str, http_request: Request, _user_id: CurrentUserId
) -> ResponseEnvelope[PreviewContextResponse]:
    context = await message_repository.get_preview_context(draft_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    return success_response(
        PreviewContextResponse.model_validate(context), meta=response_meta(http_request)
    )
