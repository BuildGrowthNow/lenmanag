"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/state/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { copyMessageDraft, createMessageDraft, listMessageDrafts, markMessageDraftReady, updateMessageDraft } from "@/lib/api/messages";
import type { GeneratedSite, LeadDetail, MessageDraft, SiteBrief } from "@/lib/types";

type MessageLeadSummary = {
  lead: LeadDetail;
  brief: SiteBrief | null;
  site: GeneratedSite | null;
  drafts: MessageDraft[];
};

type MessageDraftsWorkspaceProps = {
  leadSummaries: MessageLeadSummary[];
};

const CHANNELS = ["email", "linkedin", "whatsapp"] as const;

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}

function statusBadgeClass(status: string) {
  if (status === "ready") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "edited") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function leadOverview(lead: LeadDetail, brief: SiteBrief | null, site: GeneratedSite | null, drafts: MessageDraft[]) {
  return {
    title: lead.companyName || lead.websiteUrl,
    subtitle: `${brief?.approvalState === "approved" ? "Brief approved" : "Waiting on brief approval"} · ${site?.readinessStatus || "No site yet"}`,
    draftCount: drafts.length,
    previewUrl: drafts[0]?.previewUrl || site?.previewUrl || null,
    exportUrl: drafts[0]?.exportUrl || site?.exportMetadata?.exportPath || null,
    calendlyUrl: drafts[0]?.calendlyUrl || null
  };
}

export function MessageDraftsWorkspace({ leadSummaries }: MessageDraftsWorkspaceProps) {
  const router = useRouter();
  const [pendingLeadId, setPendingLeadId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [draftState, setDraftState] = useState<Record<string, MessageDraft[]>>(
    () => Object.fromEntries(leadSummaries.map((entry) => [entry.lead.id, entry.drafts]))
  );

  const totals = useMemo(() => {
    const allDrafts = Object.values(draftState).flat();
    return {
      totalDrafts: allDrafts.length,
      readyCount: allDrafts.filter((draft) => draft.status === "ready").length,
      editedCount: allDrafts.filter((draft) => draft.status === "edited").length
    };
  }, [draftState]);

  async function handleCreateDraft(leadId: string, channel: string) {
    setPendingLeadId(leadId);
    setMessage(null);
    try {
      await createMessageDraft(leadId, { channel });
      const payload = await listMessageDrafts(leadId);
      setDraftState((current) => ({ ...current, [leadId]: payload.items }));
      setMessage(`Created a ${channel} draft.`);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create the draft.");
    } finally {
      setPendingLeadId(null);
    }
  }

  async function handleCopy(draftId: string) {
    setPendingLeadId(draftId);
    setMessage(null);
    try {
      const copy = await copyMessageDraft(draftId);
      await navigator.clipboard.writeText(`${copy.subject}\n\n${copy.body}`);
      setMessage(`Copied ${copy.channel} draft text to the clipboard.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not copy the draft.");
    } finally {
      setPendingLeadId(null);
    }
  }

  async function handleReady(draftId: string, leadId: string) {
    setPendingLeadId(draftId);
    setMessage(null);
    try {
      await markMessageDraftReady(draftId);
      const payload = await listMessageDrafts(leadId);
      setDraftState((current) => ({ ...current, [leadId]: payload.items }));
      setMessage("Draft marked ready.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update the draft.");
    } finally {
      setPendingLeadId(null);
    }
  }

  async function handleSave(draft: MessageDraft, leadId: string) {
    setPendingLeadId(draft.id);
    setMessage(null);
    try {
      await updateMessageDraft(draft.id, {
        subject: draft.subject,
        body: draft.body,
        tone: draft.tone,
        angle: draft.angle
      });
      const payload = await listMessageDrafts(leadId);
      setDraftState((current) => ({ ...current, [leadId]: payload.items }));
      setMessage("Draft saved.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save the draft.");
    } finally {
      setPendingLeadId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Drafts</CardDescription>
            <CardTitle className="text-3xl">{totals.totalDrafts}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Edited</CardDescription>
            <CardTitle className="text-3xl">{totals.editedCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Ready</CardDescription>
            <CardTitle className="text-3xl">{totals.readyCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {message ? <div className="rounded-2xl border border-line bg-panel px-4 py-3 text-sm text-text">{message}</div> : null}

      <div className="grid gap-4 xl:grid-cols-2">
        {leadSummaries.map((entry) => {
          const drafts = draftState[entry.lead.id] || entry.drafts;
          const overview = leadOverview(entry.lead, entry.brief, entry.site, drafts);
          const primaryDraft = drafts[0] || null;

          return (
            <Card key={entry.lead.id}>
              <CardHeader>
                <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                  <div>
                    <CardTitle>{overview.title}</CardTitle>
                    <CardDescription>{overview.subtitle}</CardDescription>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{entry.lead.status}</Badge>
                    <Badge>{overview.draftCount} drafts</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm text-text">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Preview alignment</div>
                  <div className="mt-2 break-all">{overview.previewUrl || "No preview linked yet."}</div>
                  <div className="mt-1 text-xs text-muted">Export: {overview.exportUrl || "Not captured"}</div>
                  <div className="mt-1 text-xs text-muted">Calendly: {overview.calendlyUrl || "Not captured in source data"}</div>
                </div>

                {entry.brief?.approvalState === "approved" ? (
                  <div className="rounded-2xl border border-dashed border-line bg-panel/70 p-4">
                    <div className="text-sm font-medium text-text">Create a draft</div>
                    <div className="mt-1 text-xs text-muted">The copy is derived from the approved brief and generated preview.</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {CHANNELS.map((channel) => (
                        <Button key={channel} type="button" variant="secondary" disabled={pendingLeadId === entry.lead.id} onClick={() => void handleCreateDraft(entry.lead.id, channel)}>
                          {channel}
                        </Button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState title="Brief not approved yet" description="Approve the brief before creating outreach drafts." />
                )}

                {primaryDraft ? (
                  <div className="rounded-2xl border border-line bg-panel-2 p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Active draft</div>
                        <div className="mt-1 text-sm text-text">{primaryDraft.channel}</div>
                      </div>
                      <Badge className={statusBadgeClass(primaryDraft.status)}>{primaryDraft.status}</Badge>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2 text-xs text-muted">
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Subject: {primaryDraft.subject}</div>
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Tone: {primaryDraft.tone}</div>
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Angle: {primaryDraft.angle}</div>
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Version: {primaryDraft.version}</div>
                    </div>
                    <div className="whitespace-pre-wrap rounded-xl border border-line bg-panel px-3 py-2 text-sm text-text">{primaryDraft.body}</div>
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleCopy(primaryDraft.id)}>
                        Copy draft
                      </Button>
                      <Button type="button" variant="secondary" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleReady(primaryDraft.id, entry.lead.id)}>
                        Mark ready
                      </Button>
                      <Button type="button" variant="ghost" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleSave(primaryDraft, entry.lead.id)}>
                        Save current text
                      </Button>
                    </div>
                  </div>
                ) : null}

                <div className="space-y-3">
                  {drafts.length ? (
                    drafts.map((draft) => (
                      <div key={draft.id} className="rounded-2xl border border-line bg-panel-2 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <div className="text-sm font-medium text-text">{draft.channel}</div>
                            <div className="text-xs text-muted">Version {draft.version} · Updated {formatDateTime(draft.updatedAt)}</div>
                          </div>
                          <Badge className={statusBadgeClass(draft.status)}>{draft.status}</Badge>
                        </div>
                        <div className="mt-3 text-sm text-text">{draft.subject}</div>
                        <div className="mt-2 text-xs text-muted">
                          {draft.tone} · {draft.angle}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-3">
                          <Button asChild variant="secondary">
                            <Link href={`/nsa/leads/${entry.lead.id}`}>Open lead</Link>
                          </Button>
                          <Button type="button" variant="ghost" disabled={pendingLeadId === draft.id} onClick={() => void handleCopy(draft.id)}>
                            Copy text
                          </Button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <EmptyState title="No drafts yet" description="Create the first draft from the approved brief and generated preview." />
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
