"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/state/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { copyMessageDraft, createMessageDraft, getCtaVariants, getPreviewContext, getTonePresets, listMessageDrafts, markMessageDraftReady, markMessageSent, resetMessageToDraft, updateMessageDraft } from "@/lib/api/messages";
import type { CtaVariant, GeneratedSite, LeadDetail, MessageDraft, SiteBrief, TonePreset } from "@/lib/types";

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
  if (status === "sent") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "failed") return "border-red-500/40 bg-red-500/10 text-red-100";
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
  const [tonePresets, setTonePresets] = useState<TonePreset[]>([]);
  const [ctaVariants, setCtaVariants] = useState<CtaVariant[]>([]);
  const [editingDraft, setEditingDraft] = useState<MessageDraft | null>(null);
  const [previewContext, setPreviewContext] = useState<any>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const totals = useMemo(() => {
    const allDrafts = Object.values(draftState).flat();
    return {
      totalDrafts: allDrafts.length,
      readyCount: allDrafts.filter((draft) => draft.status === "ready").length,
      editedCount: allDrafts.filter((draft) => draft.status === "edited").length
    };
  }, [draftState]);

  useEffect(() => {
    async function loadPresets() {
      try {
        const [tones, ctas] = await Promise.all([getTonePresets(), getCtaVariants()]);
        setTonePresets(tones);
        setCtaVariants(ctas);
      } catch (error) {
        console.error("Failed to load presets:", error);
      }
    }
    loadPresets();
  }, []);

  useEffect(() => {
    async function loadPreviewContext() {
      if (editingDraft) {
        try {
          const context = await getPreviewContext(editingDraft.id);
          setPreviewContext(context);
        } catch (error) {
          console.error("Failed to load preview context:", error);
        }
      }
    }
    loadPreviewContext();
  }, [editingDraft]);

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
    setValidationErrors([]);
    try {
      await markMessageDraftReady(draftId);
      const payload = await listMessageDrafts(leadId);
      setDraftState((current) => ({ ...current, [leadId]: payload.items }));
      setMessage("Draft marked ready.");
      router.refresh();
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Could not update the draft.";
      setMessage(errorMsg);
      if (errorMsg.includes("Cannot mark as ready")) {
        setValidationErrors(errorMsg.split(": ")[1]?.split(", ") || [errorMsg]);
      }
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
        tonePreset: draft.tonePreset,
        customTone: draft.customTone,
        angle: draft.angle,
        ctaVariant: draft.ctaVariant,
        ctaPosition: draft.ctaPosition,
        deliveryChannel: draft.deliveryChannel,
        calendlyUrl: draft.calendlyUrl
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

  async function handleMarkSent(draftId: string, leadId: string) {
    setPendingLeadId(draftId);
    setMessage(null);
    try {
      await markMessageSent(draftId);
      const payload = await listMessageDrafts(leadId);
      setDraftState((current) => ({ ...current, [leadId]: payload.items }));
      setMessage("Draft marked as sent.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not mark as sent.");
    } finally {
      setPendingLeadId(null);
    }
  }

  async function handleResetToDraft(draftId: string, leadId: string) {
    setPendingLeadId(draftId);
    setMessage(null);
    try {
      await resetMessageToDraft(draftId);
      const payload = await listMessageDrafts(leadId);
      setDraftState((current) => ({ ...current, [leadId]: payload.items }));
      setMessage("Draft reset to draft status.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not reset draft.");
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
                  <div className="rounded-2xl border border-line bg-panel-2 p-4 space-y-3"
                    onClick={() => setEditingDraft(primaryDraft)}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Active draft</div>
                        <div className="mt-1 text-sm text-text">{primaryDraft.channel}</div>
                      </div>
                      <Badge className={statusBadgeClass(primaryDraft.status)}>{primaryDraft.status}</Badge>
                    </div>
                    
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-1">
                        <label className="text-xs uppercase tracking-[0.18em] text-muted">Delivery Channel</label>
                        <select
                          className="h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20"
                          value={primaryDraft.deliveryChannel}
                          onChange={(e) => {
                            const updated = { ...primaryDraft, deliveryChannel: e.target.value as any };
                            setDraftState((current) => ({
                              ...current,
                              [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                            }));
                          }}
                        >
                          <option value="email">Email</option>
                          <option value="linkedin">LinkedIn</option>
                          <option value="whatsapp">WhatsApp</option>
                          <option value="generic">Generic</option>
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs uppercase tracking-[0.18em] text-muted">Tone Preset</label>
                        <select
                          className="h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20"
                          value={primaryDraft.tonePreset || ""}
                          onChange={(e) => {
                            const updated = { ...primaryDraft, tonePreset: e.target.value || null };
                            setDraftState((current) => ({
                              ...current,
                              [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                            }));
                          }}
                        >
                          <option value="">None</option>
                          {tonePresets.map((preset) => (
                            <option key={preset.id} value={preset.id}>{preset.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs uppercase tracking-[0.18em] text-muted">Custom Tone</label>
                        <Input
                          value={primaryDraft.customTone || ""}
                          onChange={(e) => {
                            const updated = { ...primaryDraft, customTone: e.target.value || null };
                            setDraftState((current) => ({
                              ...current,
                              [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                            }));
                          }}
                          placeholder="Custom tone description..."
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs uppercase tracking-[0.18em] text-muted">CTA Variant</label>
                        <select
                          className="h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20"
                          value={primaryDraft.ctaVariant || ""}
                          onChange={(e) => {
                            const updated = { ...primaryDraft, ctaVariant: e.target.value || null };
                            setDraftState((current) => ({
                              ...current,
                              [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                            }));
                          }}
                        >
                          <option value="">None</option>
                          {ctaVariants.map((variant) => (
                            <option key={variant.id} value={variant.id}>{variant.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs uppercase tracking-[0.18em] text-muted">CTA Position</label>
                        <select
                          className="h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20"
                          value={primaryDraft.ctaPosition || ""}
                          onChange={(e) => {
                            const updated = { ...primaryDraft, ctaPosition: e.target.value || null };
                            setDraftState((current) => ({
                              ...current,
                              [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                            }));
                          }}
                        >
                          <option value="">None</option>
                          <option value="top">Top</option>
                          <option value="middle">Middle</option>
                          <option value="bottom">Bottom</option>
                          <option value="inline">Inline</option>
                        </select>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs uppercase tracking-[0.18em] text-muted">Calendly URL</label>
                      <Input
                        value={primaryDraft.calendlyUrl || ""}
                        onChange={(e) => {
                          const updated = { ...primaryDraft, calendlyUrl: e.target.value || null };
                          setDraftState((current) => ({
                            ...current,
                            [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                          }));
                        }}
                        placeholder="https://calendly.com/..."
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs uppercase tracking-[0.18em] text-muted">Insert CTA Link</label>
                      <select
                        className="h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20"
                        onChange={(e) => {
                          const linkType = e.target.value;
                          if (!linkType) return;
                          
                          let linkToInsert = "";
                          if (linkType === "calendly" && primaryDraft.calendlyUrl) {
                            linkToInsert = primaryDraft.calendlyUrl;
                          } else if (linkType === "preview" && primaryDraft.previewUrl) {
                            linkToInsert = primaryDraft.previewUrl;
                          } else if (linkType === "export" && primaryDraft.exportUrl) {
                            linkToInsert = primaryDraft.exportUrl;
                          }
                          
                          if (linkToInsert) {
                            const updated = { ...primaryDraft, body: `${primaryDraft.body}\n\n${linkToInsert}` };
                            setDraftState((current) => ({
                              ...current,
                              [entry.lead.id]: current[entry.lead.id]?.map((d) => d.id === primaryDraft.id ? updated : d) || [updated]
                            }));
                          }
                        }}
                      >
                        <option value="">Select link type...</option>
                        <option value="calendly">Insert Calendly Link</option>
                        <option value="preview">Insert Preview Link</option>
                        <option value="export">Insert Export Bundle Link</option>
                      </select>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2 text-xs text-muted">
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Subject: {primaryDraft.subject}</div>
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Tone: {primaryDraft.tone}</div>
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Angle: {primaryDraft.angle}</div>
                      <div className="rounded-xl border border-line bg-panel px-3 py-2">Version: {primaryDraft.version}</div>
                    </div>
                    <div className="whitespace-pre-wrap rounded-xl border border-line bg-panel px-3 py-2 text-sm text-text">{primaryDraft.body}</div>
                    
                    {validationErrors.length > 0 && (
                      <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 space-y-2">
                        <div className="text-xs uppercase tracking-[0.18em] text-red-100">Validation Errors</div>
                        {validationErrors.map((error, idx) => (
                          <div key={idx} className="text-sm text-red-100">• {error}</div>
                        ))}
                      </div>
                    )}
                    
                    {previewContext && (
                      <div className="rounded-2xl border border-line bg-panel-2 p-4 space-y-3">
                        <div className="text-xs uppercase tracking-[0.18em] text-muted">Preview Context</div>
                        {previewContext.sitePreviewUrl && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted">Site Preview</div>
                            <a 
                              href={previewContext.sitePreviewUrl} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-sm text-text hover:underline break-all"
                            >
                              {previewContext.sitePreviewUrl}
                            </a>
                          </div>
                        )}
                        {previewContext.briefSummary && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted">Brief Summary</div>
                            <div className="text-sm text-text">{previewContext.briefSummary}</div>
                          </div>
                        )}
                        <div className="grid gap-2 md:grid-cols-2 text-xs">
                          {previewContext.ctaPrimaryLabel && (
                            <div className="rounded-xl border border-line bg-panel px-3 py-2">
                              <div className="text-muted">Primary CTA</div>
                              <div className="text-text">{previewContext.ctaPrimaryLabel}</div>
                            </div>
                          )}
                          {previewContext.ctaSecondaryLabel && (
                            <div className="rounded-xl border border-line bg-panel px-3 py-2">
                              <div className="text-muted">Secondary CTA</div>
                              <div className="text-text">{previewContext.ctaSecondaryLabel}</div>
                            </div>
                          )}
                        </div>
                        {previewContext.calendlyUrl && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted">Calendly Link</div>
                            <a 
                              href={previewContext.calendlyUrl} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-sm text-text hover:underline break-all"
                            >
                              {previewContext.calendlyUrl}
                            </a>
                          </div>
                        )}
                        {previewContext.exportUrl && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted">Export Bundle</div>
                            <div className="text-sm text-text break-all">{previewContext.exportUrl}</div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleCopy(primaryDraft.id)}>
                        Copy draft
                      </Button>
                      <Button type="button" variant="secondary" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleReady(primaryDraft.id, entry.lead.id)}>
                        Mark ready
                      </Button>
                      {primaryDraft.status === "ready" && (
                        <Button type="button" variant="secondary" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleMarkSent(primaryDraft.id, entry.lead.id)}>
                          Mark sent
                        </Button>
                      )}
                      {(primaryDraft.status === "ready" || primaryDraft.status === "sent" || primaryDraft.status === "edited") && (
                        <Button type="button" variant="ghost" disabled={pendingLeadId === primaryDraft.id} onClick={() => void handleResetToDraft(primaryDraft.id, entry.lead.id)}>
                          Reset to draft
                        </Button>
                      )}
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
