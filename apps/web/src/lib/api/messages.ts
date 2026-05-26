import { request, safeRequest } from "@/lib/api/client";
import type {
  MessageCopyResponse,
  MessageDraft,
  MessageDraftCreatePayload,
  MessageDraftListResponse,
  MessageDraftPatchPayload
} from "@/lib/types";

export async function listMessageDrafts(leadId: string): Promise<MessageDraftListResponse> {
  return safeRequest<MessageDraftListResponse>(`/api/leads/${leadId}/messages`, { leadId, items: [] });
}

export async function createMessageDraft(leadId: string, payload: MessageDraftCreatePayload = {}): Promise<MessageDraft> {
  return request(`/api/leads/${leadId}/messages`, { method: "POST", body: payload });
}

export async function updateMessageDraft(draftId: string, payload: MessageDraftPatchPayload): Promise<MessageDraft> {
  return request(`/api/messages/${draftId}`, { method: "PATCH", body: payload });
}

export async function markMessageDraftReady(draftId: string): Promise<MessageDraft> {
  return request(`/api/messages/${draftId}/ready`, { method: "POST" });
}

export async function copyMessageDraft(draftId: string, channel?: string): Promise<MessageCopyResponse> {
  const query = channel ? `?channel=${encodeURIComponent(channel)}` : "";
  return request(`/api/messages/${draftId}/copy${query}`);
}
