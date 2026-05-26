from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query

from app.core.audit import write_audit_log
from app.core.messages import message_repository
from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.schemas.message import MessageCopyResponse, MessageDraft, MessageDraftCreateRequest, MessageDraftListResponse, MessageDraftPatchRequest

router = APIRouter(tags=["messages"])


async def _require_session(session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_session_token(session_cookie)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return payload


@router.post("/leads/{lead_id}/messages", response_model=MessageDraft)
async def create_message_draft(
    lead_id: str,
    request: MessageDraftCreateRequest,
    session: dict = Depends(_require_session),
) -> MessageDraft:
    draft = await message_repository.create_draft(lead_id, request)
    if draft is None:
        raise HTTPException(status_code=409, detail="Approve the brief before creating a message draft.")
    await write_audit_log(session["email"], "message", draft.id, "message_draft_create", after=draft.model_dump())
    return draft


@router.get("/leads/{lead_id}/messages", response_model=MessageDraftListResponse)
async def list_message_drafts(lead_id: str, session: dict = Depends(_require_session)) -> MessageDraftListResponse:
    return await message_repository.list_drafts(lead_id)


@router.patch("/messages/{draft_id}", response_model=MessageDraft)
async def patch_message_draft(
    draft_id: str,
    request: MessageDraftPatchRequest,
    session: dict = Depends(_require_session),
) -> MessageDraft:
    before = await message_repository.get_copy(draft_id)
    draft = await message_repository.update_draft(draft_id, request)
    if draft is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(session["email"], "message", draft.id, "message_draft_edit", before=before.model_dump() if before else None, after=draft.model_dump())
    return draft


@router.post("/messages/{draft_id}/ready", response_model=MessageDraft)
async def mark_message_ready(draft_id: str, session: dict = Depends(_require_session)) -> MessageDraft:
    before = await message_repository.get_copy(draft_id)
    draft = await message_repository.mark_ready(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(session["email"], "message", draft.id, "message_marked_ready", before=before.model_dump() if before else None, after=draft.model_dump())
    return draft


@router.get("/messages/{draft_id}/copy", response_model=MessageCopyResponse)
async def copy_message_draft(
    draft_id: str,
    channel: str | None = Query(default=None),
    session: dict = Depends(_require_session),
) -> MessageCopyResponse:
    copy = await message_repository.get_copy(draft_id, channel=channel)
    if copy is None:
        raise HTTPException(status_code=404, detail="Message draft not found.")
    await write_audit_log(session["email"], "message", draft_id, "message_copy_requested", after={"channel": copy.channel, "status": copy.status})
    return copy
