"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/state/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import {
  bulkGenerateMessageDrafts,
  copyMessageDraft,
  createMessageDraft,
  getPreviewContext,
  listMessageDrafts,
  markMessageDraftReady,
  markMessageSent,
  resetMessageToDraft,
  updateMessageDraft,
} from "@/lib/api/messages";
import type {
  CtaVariant,
  DeliveryChannel,
  GeneratedSite,
  LeadDetail,
  MasterBrief,
  MessageDraft,
  TonePreset,
} from "@/lib/types";

const TONE_PRESETS: TonePreset[] = [
  { id: "professional", name: "Professional", description: "Formal and business-focused tone", example: "I hope this message finds you well. I would like to discuss…" },
  { id: "casual", name: "Casual", description: "Relaxed and conversational tone", example: "Hey! Just wanted to reach out about…" },
  { id: "urgent", name: "Urgent", description: "Time-sensitive and action-oriented tone", example: "Quick update - time is of the essence for…" },
  { id: "friendly", name: "Friendly", description: "Warm and approachable tone", example: "Hi there! I'm excited to share with you…" },
];

const CTA_VARIANTS: CtaVariant[] = [
  { id: "primary", name: "Primary CTA", description: "Main call-to-action for the message", label: "Review the preview", position: "bottom" },
  { id: "secondary", name: "Secondary CTA", description: "Alternative call-to-action", label: "See source notes", position: "bottom" },
  { id: "tertiary", name: "Tertiary CTA", description: "Additional call-to-action option", label: "Learn more", position: "inline" },
];
import { cn } from "@/lib/utils";

type MessageLeadSummary = {
  lead: LeadDetail;
  brief: MasterBrief | null;
  site: GeneratedSite | null;
  drafts: MessageDraft[];
};

type MessageDraftsWorkspaceProps = {
  leadSummaries: MessageLeadSummary[];
};

const CHANNELS = ["email", "linkedin", "whatsapp"] as const;
type Channel = (typeof CHANNELS)[number];

function statusBadgeClass(status: string) {
  if (status === "ready") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "edited") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  if (status === "sent") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "failed") return "border-red-500/40 bg-red-500/10 text-red-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function statusLabel(status: string) {
  if (status === "ready") return "Ready";
  if (status === "edited") return "Edited";
  if (status === "sent") return "Sent";
  if (status === "failed") return "Failed";
  return "Draft";
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs uppercase tracking-[0.16em] text-muted">{label}</label>
      {children}
    </div>
  );
}

export function MessageDraftsWorkspace({ leadSummaries }: MessageDraftsWorkspaceProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "draft" | "edited" | "ready">("all");
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(
    leadSummaries[0]?.lead.id ?? null
  );
  const [activeChannel, setActiveChannel] = useState<Channel>("email");
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [dirtyDraftIds, setDirtyDraftIds] = useState<Set<string>>(new Set());

  const [draftState, setDraftState] = useState<Record<string, MessageDraft[]>>(
    () => Object.fromEntries(leadSummaries.map((e) => [e.lead.id, e.drafts]))
  );
  const [previewContexts, setPreviewContexts] = useState<Record<string, unknown>>({});

  const allDrafts = useMemo(() => Object.values(draftState).flat(), [draftState]);

  const filteredLeads = useMemo(() => {
    return leadSummaries.filter((e) => {
      const name = (e.lead.companyName ?? e.lead.websiteUrl).toLowerCase();
      if (search && !name.includes(search.toLowerCase())) return false;
      const drafts = draftState[e.lead.id] ?? [];
      if (filterStatus === "all") return true;
      return drafts.some((d) => d.status === filterStatus);
    });
  }, [leadSummaries, draftState, search, filterStatus]);

  const selectedEntry = useMemo(
    () => leadSummaries.find((e) => e.lead.id === selectedLeadId) ?? null,
    [leadSummaries, selectedLeadId]
  );

  const activeDraft = useMemo(() => {
    if (!selectedLeadId) return null;
    const drafts = draftState[selectedLeadId] ?? [];
    return drafts.find((d) => d.deliveryChannel === activeChannel || d.channel === activeChannel) ?? drafts[0] ?? null;
  }, [draftState, selectedLeadId, activeChannel]);

  const activeDraftId = activeDraft?.id;
  useEffect(() => {
    if (!activeDraftId) return;
    getPreviewContext(activeDraftId)
      .then((ctx) => setPreviewContexts((prev) => ({ ...prev, [activeDraftId]: ctx })))
      .catch(console.error);
  }, [activeDraftId]);

  function showNotice(type: "ok" | "err", text: string) {
    setNotice({ type, text });
    setTimeout(() => setNotice(null), 4000);
  }

  async function refreshDrafts(leadId: string) {
    const payload = await listMessageDrafts(leadId);
    setDraftState((prev) => ({ ...prev, [leadId]: payload.items }));
    setDirtyDraftIds((prev) => {
      const next = new Set(prev);
      payload.items.forEach((d) => next.delete(d.id));
      return next;
    });
    router.refresh();
  }

  async function handleCreateDraft(leadId: string, channel: string) {
    setPendingId(leadId + channel);
    setNotice(null);
    try {
      await createMessageDraft(leadId, { channel });
      await refreshDrafts(leadId);
      setActiveChannel(channel as Channel);
      showNotice("ok", `Created a ${channel} draft.`);
    } catch (e) {
      showNotice("err", e instanceof Error ? e.message : "Could not create draft.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleSave(draft: MessageDraft, leadId: string) {
    setPendingId(draft.id);
    setNotice(null);
    try {
      await updateMessageDraft(draft.id, {
        subject: draft.subject,
        body: draft.body,
        tone: draft.tone,
        tonePreset: draft.tonePreset,
        customTone: draft.customTone,
        angle: draft.angle,
        ctaVariant: draft.ctaVariant,
        ctaPosition: draft.ctaPosition,
        deliveryChannel: draft.deliveryChannel,
        calendlyUrl: draft.calendlyUrl,
      });
      await refreshDrafts(leadId);
      showNotice("ok", "Draft saved.");
    } catch (e) {
      showNotice("err", e instanceof Error ? e.message : "Could not save draft.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleMarkReady(draftId: string, leadId: string) {
    setPendingId(draftId);
    setNotice(null);
    setValidationErrors([]);
    try {
      await markMessageDraftReady(draftId);
      await refreshDrafts(leadId);
      showNotice("ok", "Draft marked ready.");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not mark ready.";
      showNotice("err", msg);
      const match = msg.match(/Cannot mark as ready: (.+)/);
      if (match) {
        setValidationErrors(match[1].split(", "));
      }
    } finally {
      setPendingId(null);
    }
  }

  async function handleMarkSent(draftId: string, leadId: string) {
    setPendingId(draftId);
    setNotice(null);
    try {
      await markMessageSent(draftId);
      await refreshDrafts(leadId);
      showNotice("ok", "Draft marked as sent.");
    } catch (e) {
      showNotice("err", e instanceof Error ? e.message : "Could not mark as sent.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleReset(draftId: string, leadId: string) {
    setPendingId(draftId);
    setNotice(null);
    try {
      await resetMessageToDraft(draftId);
      await refreshDrafts(leadId);
      showNotice("ok", "Draft reset.");
    } catch (e) {
      showNotice("err", e instanceof Error ? e.message : "Could not reset draft.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleCopy(draftId: string) {
    setPendingId(draftId);
    setNotice(null);
    try {
      const copy = await copyMessageDraft(draftId);
      await navigator.clipboard.writeText(`${copy.subject}\n\n${copy.body}`);
      showNotice("ok", "Copied to clipboard.");
    } catch (e) {
      showNotice("err", e instanceof Error ? e.message : "Could not copy.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleBulkGenerate(leadId: string) {
    setPendingId(leadId + "_bulk");
    setNotice(null);
    try {
      await bulkGenerateMessageDrafts(leadId, { force: false });
      await refreshDrafts(leadId);
      showNotice("ok", "AI drafted email, LinkedIn, and WhatsApp messages.");
    } catch (e) {
      showNotice("err", e instanceof Error ? e.message : "Could not generate drafts.");
    } finally {
      setPendingId(null);
    }
  }

  function patchActiveDraft(patch: Partial<MessageDraft>) {
    if (!activeDraft || !selectedLeadId) return;
    setDraftState((prev) => ({
      ...prev,
      [selectedLeadId]: (prev[selectedLeadId] ?? []).map((d) =>
        d.id === activeDraft.id ? { ...d, ...patch } : d
      ),
    }));
    setDirtyDraftIds((prev) => new Set(prev).add(activeDraft.id));
  }

  const previewCtx = activeDraft ? (previewContexts[activeDraft.id] as Record<string, unknown> | undefined) : undefined;

  return (
    <div className="flex h-[calc(100vh-14rem)] min-h-[600px] gap-0 overflow-hidden rounded-2xl border border-line">
      {/* Left: lead list */}
      <div className="flex w-[300px] shrink-0 flex-col border-r border-line">
        {/* Search + filter */}
        <div className="border-b border-line p-3 space-y-2">
          <Input
            placeholder="Search by company…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9"
          />
          <div className="flex gap-1.5 flex-wrap">
            {(["all", "draft", "edited", "ready"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilterStatus(f)}
                className={cn(
                  "rounded-md px-2 py-0.5 text-xs capitalize transition-colors",
                  filterStatus === f
                    ? "bg-text text-bg"
                    : "text-muted hover:text-text"
                )}
              >
                {f === "all" ? `All ${leadSummaries.length}` : f}
              </button>
            ))}
          </div>
        </div>

        {/* Lead list */}
        <div className="flex-1 overflow-y-auto">
          {filteredLeads.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-muted">No leads match.</div>
          ) : (
            filteredLeads.map((entry) => {
              const drafts = draftState[entry.lead.id] ?? [];
              const name = entry.lead.companyName ?? entry.lead.websiteUrl;
              const domain = entry.lead.normalizedDomain;
              const readyDrafts = drafts.filter((d) => d.status === "ready").length;
              const latestDraft = drafts[0] ?? null;
              const isSelected = selectedLeadId === entry.lead.id;

              return (
                <button
                  key={entry.lead.id}
                  onClick={() => {
                    setSelectedLeadId(entry.lead.id);
                    if (latestDraft) {
                      setActiveChannel((latestDraft.deliveryChannel ?? latestDraft.channel) as Channel);
                    }
                  }}
                  className={cn(
                    "w-full border-b border-line px-4 py-3 text-left transition-colors hover:bg-panel",
                    isSelected && "bg-panel"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-text">{name}</div>
                      <div className="truncate text-xs text-muted">{domain}</div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      {latestDraft ? (
                        <Badge className={cn("text-[10px]", statusBadgeClass(latestDraft.status))}>
                          {statusLabel(latestDraft.status)}
                        </Badge>
                      ) : (
                        <Badge className="text-[10px] border-zinc-500/40 bg-zinc-500/10 text-zinc-400">
                          No draft
                        </Badge>
                      )}
                      {readyDrafts > 0 && (
                        <span className="text-[10px] text-emerald-400">{readyDrafts} ready</span>
                      )}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    {drafts.length} draft{drafts.length !== 1 ? "s" : ""}
                    {latestDraft ? ` · ${relativeTime(latestDraft.updatedAt)}` : ""}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Summary strip */}
        <div className="border-t border-line px-4 py-3 grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-lg font-semibold text-text">{allDrafts.length}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted">Total</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-amber-400">
              {allDrafts.filter((d) => d.status === "edited").length}
            </div>
            <div className="text-[10px] uppercase tracking-widest text-muted">Edited</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-emerald-400">
              {allDrafts.filter((d) => d.status === "ready").length}
            </div>
            <div className="text-[10px] uppercase tracking-widest text-muted">Ready</div>
          </div>
        </div>
      </div>

      {/* Right: workspace */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {!selectedEntry ? (
          <div className="flex flex-1 items-center justify-center">
            <EmptyState title="Select a lead" description="Choose a lead from the list to view and edit outreach drafts." />
          </div>
        ) : (
          <>
            {/* Workspace header */}
            <div className="border-b border-line px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-base font-semibold text-text">
                    {selectedEntry.lead.companyName ?? selectedEntry.lead.websiteUrl}
                  </div>
                  <div className="mt-0.5 text-sm text-muted">{selectedEntry.lead.normalizedDomain}</div>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={`/compare/${selectedEntry.lead.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-1.5 text-xs font-medium text-yellow-300 transition-colors hover:bg-yellow-500/20"
                  >
                    Compare all ↗
                  </a>
                  {selectedEntry.site?.previewUrl && (
                    <a
                      href={selectedEntry.site.previewUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted transition-colors hover:text-text"
                    >
                      Preview ↗
                    </a>
                  )}
                  <Link
                    href={`/app/leads/${selectedEntry.lead.id}`}
                    className="rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted transition-colors hover:text-text"
                  >
                    View lead
                  </Link>
                </div>
              </div>

              {/* Channel tabs */}
              <div className="mt-4 flex gap-1">
                {CHANNELS.map((ch) => {
                  const drafts = draftState[selectedEntry.lead.id] ?? [];
                  const hasDraft = drafts.some((d) => d.deliveryChannel === ch || d.channel === ch);
                  return (
                    <button
                      key={ch}
                      onClick={() => setActiveChannel(ch)}
                      className={cn(
                        "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm capitalize transition-colors",
                        activeChannel === ch
                          ? "border-text/30 bg-panel text-text"
                          : "border-transparent text-muted hover:text-text"
                      )}
                    >
                      {ch}
                      {hasDraft && (
                        <span className={cn(
                          "h-1.5 w-1.5 rounded-full",
                          activeChannel === ch ? "bg-text" : "bg-muted"
                        )} />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Notice bar */}
            {notice && (
              <div
                className={cn(
                  "px-6 py-2 text-sm",
                  notice.type === "ok"
                    ? "bg-emerald-500/10 text-emerald-200"
                    : "bg-red-500/10 text-red-200"
                )}
              >
                {notice.text}
              </div>
            )}

            {/* Workspace body */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {/* Brief not ready */}
              {selectedEntry.brief === null && !activeDraft ? (
                <EmptyState
                  title="No brief found"
                  description="The brief could not be loaded. Check the lead detail page to create or approve one."
                />
              ) : selectedEntry.brief?.approvalState !== "approved" && !activeDraft ? (
                <EmptyState
                  title="Brief not approved yet"
                  description="Approve the brief before creating outreach drafts for this lead."
                />
              ) : !activeDraft ? (
                /* No draft for this channel */
                <div className="rounded-2xl border border-dashed border-line bg-panel/60 p-6 space-y-5">
                  <div>
                    <div className="text-sm font-medium text-text">No {activeChannel} draft yet</div>
                    <div className="mt-1 text-xs text-muted">
                      Use AI to draft all 3 channels at once, or create a single draft manually.
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      disabled={pendingId === selectedEntry.lead.id + "_bulk"}
                      onClick={() => void handleBulkGenerate(selectedEntry.lead.id)}
                    >
                      {pendingId === selectedEntry.lead.id + "_bulk" ? "Generating…" : "Generate all 3 with AI"}
                    </Button>
                    {CHANNELS.map((ch) => (
                      <Button
                        key={ch}
                        type="button"
                        variant="secondary"
                        disabled={pendingId === selectedEntry.lead.id + ch}
                        onClick={() => void handleCreateDraft(selectedEntry.lead.id, ch)}
                      >
                        {ch}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Draft editor */
                <div className="space-y-5">
                  {/* Status + meta */}
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Badge className={statusBadgeClass(activeDraft.status)}>
                        {statusLabel(activeDraft.status)}
                      </Badge>
                      <span className="text-xs text-muted">
                        v{activeDraft.version} · {relativeTime(activeDraft.updatedAt)}
                      </span>
                      {dirtyDraftIds.has(activeDraft.id) && (
                        <span className="text-xs text-amber-400">Unsaved changes</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {CHANNELS.map((ch) => {
                        const drafts = draftState[selectedEntry.lead.id] ?? [];
                        const hasDraft = drafts.some((d) => d.deliveryChannel === ch || d.channel === ch);
                        if (hasDraft) return null;
                        return (
                          <Button
                            key={ch}
                            type="button"
                            variant="ghost"
                            disabled={pendingId === selectedEntry.lead.id + ch}
                            onClick={() => void handleCreateDraft(selectedEntry.lead.id, ch)}
                          >
                            + {ch}
                          </Button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <FieldRow label="Delivery channel">
                      <Select
                        value={activeDraft.deliveryChannel}
                        onChange={(e) => patchActiveDraft({ deliveryChannel: e.target.value as DeliveryChannel })}
                      >
                        <option value="email">Email</option>
                        <option value="linkedin">LinkedIn</option>
                        <option value="whatsapp">WhatsApp</option>
                        <option value="generic">Generic</option>
                      </Select>
                    </FieldRow>
                    <FieldRow label="Tone preset">
                      <Select
                        value={activeDraft.tonePreset ?? ""}
                        onChange={(e) => patchActiveDraft({ tonePreset: e.target.value || null })}
                      >
                        <option value="">None</option>
                        {TONE_PRESETS.map((p) => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </Select>
                    </FieldRow>
                    <FieldRow label="Custom tone">
                      <Input
                        value={activeDraft.customTone ?? ""}
                        onChange={(e) => patchActiveDraft({ customTone: e.target.value || null })}
                        placeholder="Custom tone description…"
                      />
                    </FieldRow>
                    <FieldRow label="CTA variant">
                      <Select
                        value={activeDraft.ctaVariant ?? ""}
                        onChange={(e) => patchActiveDraft({ ctaVariant: e.target.value || null })}
                      >
                        <option value="">None</option>
                        {CTA_VARIANTS.map((v) => (
                          <option key={v.id} value={v.id}>{v.name}</option>
                        ))}
                      </Select>
                    </FieldRow>
                    <FieldRow label="CTA position">
                      <Select
                        value={activeDraft.ctaPosition ?? ""}
                        onChange={(e) => patchActiveDraft({ ctaPosition: e.target.value || null })}
                      >
                        <option value="">None</option>
                        <option value="top">Top</option>
                        <option value="middle">Middle</option>
                        <option value="bottom">Bottom</option>
                        <option value="inline">Inline</option>
                      </Select>
                    </FieldRow>
                    <FieldRow label="Calendly URL">
                      <Input
                        value={activeDraft.calendlyUrl ?? ""}
                        onChange={(e) => patchActiveDraft({ calendlyUrl: e.target.value || null })}
                        placeholder="https://calendly.com/…"
                      />
                    </FieldRow>
                  </div>

                  <div className="h-px bg-line" />

                  <FieldRow label="Subject">
                    <Input
                      value={activeDraft.subject}
                      onChange={(e) => patchActiveDraft({ subject: e.target.value })}
                      placeholder="Email subject…"
                    />
                  </FieldRow>

                  <FieldRow label="Body">
                    <div className="relative">
                      <Textarea
                        value={activeDraft.body}
                        onChange={(e) => patchActiveDraft({ body: e.target.value })}
                        className="min-h-48"
                        placeholder="Message body…"
                      />
                      {/* Insert link helper */}
                      <div className="mt-1 flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] text-muted">Insert:</span>
                        {activeDraft.calendlyUrl && (
                          <button
                            className="text-[11px] text-muted underline-offset-2 hover:text-text hover:underline"
                            onClick={() => patchActiveDraft({ body: `${activeDraft.body}\n\n${activeDraft.calendlyUrl}` })}
                          >
                            Calendly
                          </button>
                        )}
                        {activeDraft.previewUrl && (
                          <button
                            className="text-[11px] text-muted underline-offset-2 hover:text-text hover:underline"
                            onClick={() => patchActiveDraft({ body: `${activeDraft.body}\n\n${activeDraft.previewUrl}` })}
                          >
                            Preview link
                          </button>
                        )}
                        {activeDraft.compareUrl && (
                          <button
                            className="text-[11px] text-yellow-400/80 underline-offset-2 hover:text-yellow-300 hover:underline"
                            onClick={() => patchActiveDraft({ body: `${activeDraft.body}\n\n${activeDraft.compareUrl}` })}
                          >
                            All variants link
                          </button>
                        )}
                        {activeDraft.exportUrl && (
                          <button
                            className="text-[11px] text-muted underline-offset-2 hover:text-text hover:underline"
                            onClick={() => patchActiveDraft({ body: `${activeDraft.body}\n\n${activeDraft.exportUrl}` })}
                          >
                            Export bundle
                          </button>
                        )}
                      </div>
                    </div>
                  </FieldRow>

                  {/* Brief summary context */}
                  {previewCtx && (
                    <div className="rounded-2xl border border-line bg-panel/60 p-4 space-y-3">
                      <div className="text-xs uppercase tracking-[0.16em] text-muted">Generated from</div>
                      {typeof previewCtx.briefSummary === "string" && previewCtx.briefSummary && (
                        <div className="text-sm text-text">{previewCtx.briefSummary}</div>
                      )}
                      <div className="flex flex-wrap gap-2">
                        <a
                          href={`/compare/${selectedEntry.lead.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-1.5 text-xs font-medium text-yellow-300 transition-colors hover:bg-yellow-500/20"
                        >
                          All variants ↗
                        </a>
                        {typeof previewCtx.sitePreviewUrl === "string" && previewCtx.sitePreviewUrl && (
                          <a
                            href={previewCtx.sitePreviewUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted transition-colors hover:text-text"
                          >
                            Site preview ↗
                          </a>
                        )}
                        {typeof previewCtx.calendlyUrl === "string" && previewCtx.calendlyUrl && (
                          <a
                            href={previewCtx.calendlyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted transition-colors hover:text-text"
                          >
                            Calendly ↗
                          </a>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Validation errors */}
                  {validationErrors.length > 0 && (
                    <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 space-y-1">
                      <div className="text-xs uppercase tracking-[0.16em] text-red-300">Validation</div>
                      {validationErrors.map((err, i) => (
                        <div key={i} className="text-sm text-red-200">• {err}</div>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button
                      type="button"
                      disabled={pendingId === activeDraft.id}
                      onClick={() => void handleSave(activeDraft, selectedEntry.lead.id)}
                    >
                      Save draft
                    </Button>
                    {activeDraft.status !== "ready" && activeDraft.status !== "sent" && (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={pendingId === activeDraft.id}
                        onClick={() => void handleMarkReady(activeDraft.id, selectedEntry.lead.id)}
                      >
                        Mark ready →
                      </Button>
                    )}
                    {activeDraft.status === "ready" && (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={pendingId === activeDraft.id}
                        onClick={() => void handleMarkSent(activeDraft.id, selectedEntry.lead.id)}
                      >
                        Mark sent
                      </Button>
                    )}
                    {(activeDraft.status === "ready" || activeDraft.status === "sent" || activeDraft.status === "edited") && (
                      <Button
                        type="button"
                        variant="ghost"
                        disabled={pendingId === activeDraft.id}
                        onClick={() => void handleReset(activeDraft.id, selectedEntry.lead.id)}
                      >
                        Reset to draft
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={pendingId === activeDraft.id}
                      onClick={() => void handleCopy(activeDraft.id)}
                    >
                      Copy text
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
