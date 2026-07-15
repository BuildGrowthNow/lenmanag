"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  approveSiteReview,
  getSiteHandoffRecord,
  getSiteReviewRecord,
  patchSiteReview,
  republishSite,
  submitSiteReview
} from "@/lib/api/sites";
import type {
  SiteHandoffRecord,
  SiteReviewChecklistItem,
  SiteReviewQueueItem,
  SiteReviewQueueResponse,
  SiteReviewRecord,
  SiteScreenshotMetadata,
  SiteQaStatus
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function statusTone(status: string) {
  if (status === "approved" || status === "pass" || status === "ready_to_publish") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  }
  if (status === "warn" || status === "ready_for_review") {
    return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  }
  if (status === "blocked" || status === "fail") {
    return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  }
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function deriveChecklist(item: SiteReviewQueueItem): SiteReviewChecklistItem[] {
  if (!item.reviewRubric.length) {
    return [];
  }
  return item.reviewRubric.map((check) => ({
    key: check.key,
    label: check.label,
    status: check.status,
    notes: check.notes,
    evidence: check.evidence ?? null
  }));
}

function newScreenshot(label: string, url: string): SiteScreenshotMetadata {
  const id = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
  return {
    id,
    label,
    url,
    capturedAt: new Date().toISOString(),
    width: null,
    height: null,
    contentHash: null,
    notes: null
  };
}

type SiteReviewQueueProps = {
  queue: SiteReviewQueueResponse;
};

export function SiteReviewQueue({ queue }: SiteReviewQueueProps) {
  const router = useRouter();
  const [selected, setSelected] = useState<SiteReviewQueueItem | null>(null);
  const [reviewRecord, setReviewRecord] = useState<SiteReviewRecord | null>(null);
  const [handoffRecord, setHandoffRecord] = useState<SiteHandoffRecord | null>(null);
  const [form, setForm] = useState({
    browserPreviewUrl: "",
    outcome: "warn" as SiteQaStatus,
    notes: "",
    blockedReason: ""
  });
  const [checklist, setChecklist] = useState<SiteReviewChecklistItem[]>([]);
  const [screenshots, setScreenshots] = useState<SiteScreenshotMetadata[]>([]);
  const [newShot, setNewShot] = useState({ label: "", url: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const automationCards = [
    { label: "Ready for automation", value: queue.automationSummary.ready },
    { label: "Needs review", value: queue.automationSummary.needsReview },
    { label: "Blocked", value: queue.automationSummary.blocked },
    { label: "Regeneration backlog", value: queue.automationSummary.regenerationBacklog }
  ];

  async function openReview(item: SiteReviewQueueItem) {
    setSelected(item);
    setMessage(null);
    setHandoffRecord(null);
    setBusy(true);
    try {
      const record = await getSiteReviewRecord(item.siteId);
      setReviewRecord(record);
      setForm({
        browserPreviewUrl: record?.browserPreviewUrl ?? item.previewUrl,
        outcome: record?.outcome ?? (item.qaStatus === "fail" ? "fail" : "warn"),
        notes: record?.notes ?? "",
        blockedReason: record?.blockedReason ?? ""
      });
      setChecklist(record?.checklist?.length ? record.checklist : deriveChecklist(item));
      setScreenshots(record?.screenshots ?? []);
    } catch (error) {
      const err = error instanceof Error ? error.message : "Failed to load review.";
      setMessage(err);
      setReviewRecord(null);
      setChecklist(deriveChecklist(item));
      setScreenshots([]);
      setForm({
        browserPreviewUrl: item.previewUrl,
        outcome: item.qaStatus === "fail" ? "fail" : "warn",
        notes: "",
        blockedReason: ""
      });
    } finally {
      setBusy(false);
    }
  }

  function updateChecklist(key: string, field: "status" | "notes", value: string) {
    setChecklist((items) =>
      items.map((entry) =>
        entry.key === key
          ? {
              ...entry,
              [field]: value
            }
          : entry
      )
    );
  }

  function removeScreenshot(id: string) {
    setScreenshots((items) => items.filter((item) => item.id !== id));
  }

  function addScreenshot() {
    if (!newShot.label.trim() || !newShot.url.trim()) {
      return;
    }
    setScreenshots((items) => [...items, newScreenshot(newShot.label.trim(), newShot.url.trim())]);
    setNewShot({ label: "", url: "" });
  }

  async function saveReview() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    const payload = {
      browserPreviewUrl: form.browserPreviewUrl || null,
      outcome: form.outcome,
      checklist,
      screenshots,
      notes: form.notes || null,
      blockedReason: form.blockedReason || null
    };
    try {
      const record = reviewRecord
        ? await patchSiteReview(selected.siteId, payload)
        : await submitSiteReview(selected.siteId, payload);
      setReviewRecord(record);
      setMessage("Review saved.");
      router.refresh();
    } catch (error) {
      const err = error instanceof Error ? error.message : "Review save failed.";
      setMessage(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleApprove() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    try {
      const record = await approveSiteReview(selected.siteId);
      setHandoffRecord(record);
      setMessage("Review approved and handoff record created.");
      router.refresh();
    } catch (error) {
      const err = error instanceof Error ? error.message : "Approval failed.";
      setMessage(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRegenerate() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    try {
      await republishSite(selected.siteId);
      setMessage("Regeneration job queued.");
      router.refresh();
    } catch (error) {
      const err = error instanceof Error ? error.message : "Regeneration failed.";
      setMessage(err);
    } finally {
      setBusy(false);
    }
  }

  async function loadHandoffRecord() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    try {
      const record = await getSiteHandoffRecord(selected.siteId);
      setHandoffRecord(record);
      setMessage(record ? "Loaded latest handoff record." : "No handoff record yet.");
    } catch (error) {
      const err = error instanceof Error ? error.message : "Could not load handoff record.";
      setMessage(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {automationCards.map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl">{card.value.toLocaleString()}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Design diversity coverage</CardTitle>
          <CardDescription>Quick pulse on how diverse the queue is right now across themes, palettes, motion, and spacing.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Themes</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(queue.themeDiversity).map(([theme, count]) => (
                <Badge key={theme} className="border-line bg-panel text-sm">
                  {theme}: {count}
                </Badge>
              ))}
              {!Object.keys(queue.themeDiversity).length ? <span className="text-sm text-muted">No themes recorded yet.</span> : null}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Palette modes</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(queue.paletteDiversity).map(([palette, count]) => (
                <Badge key={palette} className="border-line bg-panel text-sm">
                  {palette}: {count}
                </Badge>
              ))}
              {!Object.keys(queue.paletteDiversity).length ? <span className="text-sm text-muted">No palette data yet.</span> : null}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Motion presets</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(queue.motionDiversity).map(([motion, count]) => (
                <Badge key={motion} className="border-line bg-panel text-sm">
                  {motion}: {count}
                </Badge>
              ))}
              {!Object.keys(queue.motionDiversity).length ? <span className="text-sm text-muted">No motion data yet.</span> : null}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Spacing styles</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(queue.spacingDiversity).map(([spacing, count]) => (
                <Badge key={spacing} className="border-line bg-panel text-sm">
                  {spacing}: {count}
                </Badge>
              ))}
              {!Object.keys(queue.spacingDiversity).length ? <span className="text-sm text-muted">No spacing data yet.</span> : null}
            </div>
          </div>
        </CardContent>
      </Card>

      {message ? <div className="rounded-2xl border border-line bg-panel p-4 text-sm text-text">{message}</div> : null}

      <div className="space-y-4">
        {queue.items.map((item) => (
          <Card key={item.siteId}>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle>{item.leadId}</CardTitle>
                  <CardDescription>Preview v{item.version} · Updated {formatDate(item.updatedAt)}</CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={statusTone(item.reviewState)}>{item.reviewState}</Badge>
                  <Badge className={statusTone(item.qaStatus)}>{item.qaStatus}</Badge>
                  <Badge className={statusTone(item.publishApprovalState)}>{item.publishApprovalState}</Badge>
                  <Button variant="secondary" onClick={() => openReview(item)} disabled={busy && selected?.siteId !== item.siteId}>
                    {selected?.siteId === item.siteId ? "Reviewing" : "Review"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm text-text">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Missing requirements</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {item.missingRequirements.length ? (
                      item.missingRequirements.map((req) => (
                        <Badge key={req} className="border-amber-500/40 bg-amber-500/10 text-amber-100">
                          {req}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-muted">None</span>
                    )}
                  </div>
                </div>
                <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm text-text">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Theme / palette</div>
                  <div className="mt-2 space-y-1">
                    <div>Theme: {item.themeKey}</div>
                    <div>Palette: {item.paletteMode}</div>
                    <div>Quality score: {item.qualityScore}</div>
                  </div>
                </div>
              </div>

              {selected?.siteId === item.siteId ? (
                <div className="space-y-4 rounded-2xl border border-line bg-panel p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="text-sm">
                      <span className="text-xs uppercase tracking-[0.18em] text-muted">Browser preview URL</span>
                      <Input
                        className="mt-2"
                        value={form.browserPreviewUrl}
                        onChange={(event) => setForm((current) => ({ ...current, browserPreviewUrl: event.target.value }))}
                      />
                    </label>
                    <label className="text-sm">
                      <span className="text-xs uppercase tracking-[0.18em] text-muted">Outcome</span>
                      <select
                        className="mt-2 h-10 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text"
                        value={form.outcome}
                        onChange={(event) => setForm((current) => ({ ...current, outcome: event.target.value as SiteQaStatus }))}
                      >
                        <option value="pass">pass</option>
                        <option value="warn">warn</option>
                        <option value="fail">fail</option>
                      </select>
                    </label>
                  </div>
                  <label className="text-sm">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Notes</span>
                    <Textarea
                      className="mt-2"
                      rows={3}
                      value={form.notes}
                      onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                      placeholder="Reviewer notes"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Blocked reason</span>
                    <Textarea
                      className="mt-2"
                      rows={2}
                      value={form.blockedReason}
                      onChange={(event) => setForm((current) => ({ ...current, blockedReason: event.target.value }))}
                      placeholder="Explain why this preview is blocked, if applicable"
                    />
                  </label>

                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Checklist</div>
                    <div className="mt-3 space-y-3">
                      {checklist.length ? (
                        checklist.map((entry) => (
                          <div key={entry.key} className="rounded-xl border border-line bg-panel-2 p-3 text-sm text-text">
                            <div className="flex flex-wrap items-center gap-3">
                              <span className="font-medium">{entry.label}</span>
                              <select
                                className="rounded-xl border border-line bg-panel px-2 py-1 text-xs"
                                value={entry.status}
                                onChange={(event) => updateChecklist(entry.key, "status", event.target.value)}
                              >
                                <option value="pass">pass</option>
                                <option value="warn">warn</option>
                                <option value="fail">fail</option>
                              </select>
                            </div>
                            <Textarea
                              className="mt-2 text-sm"
                              rows={2}
                              value={entry.notes}
                              onChange={(event) => updateChecklist(entry.key, "notes", event.target.value)}
                              placeholder="Add reviewer notes"
                            />
                          </div>
                        ))
                      ) : (
                        <div className="rounded-xl border border-dashed border-line bg-panel-2 p-3 text-sm text-muted">No checklist items.</div>
                      )}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-muted">Screenshots</div>
                    <div className="mt-2 space-y-3">
                      {screenshots.map((shot) => (
                        <div key={shot.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-panel-2 p-3 text-sm">
                          <div className="flex-1">
                            <div className="font-medium text-text">{shot.label}</div>
                            <div className="text-xs text-muted">{shot.url}</div>
                          </div>
                          <Button type="button" variant="ghost" onClick={() => removeScreenshot(shot.id)}>
                            Remove
                          </Button>
                        </div>
                      ))}
                      <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                        <Input
                          placeholder="Label"
                          value={newShot.label}
                          onChange={(event) => setNewShot((current) => ({ ...current, label: event.target.value }))}
                        />
                        <Input
                          placeholder="https://..."
                          value={newShot.url}
                          onChange={(event) => setNewShot((current) => ({ ...current, url: event.target.value }))}
                        />
                        <Button type="button" variant="secondary" onClick={addScreenshot}>
                          Add screenshot
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <Button type="button" onClick={saveReview} disabled={busy}>
                      {busy ? "Saving..." : "Save review"}
                    </Button>
                    <Button type="button" variant="secondary" onClick={handleApprove} disabled={busy}>
                      Approve & publish
                    </Button>
                    <Button type="button" variant="ghost" onClick={handleRegenerate} disabled={busy}>
                      Regenerate preview
                    </Button>
                    <Button type="button" variant="ghost" onClick={loadHandoffRecord} disabled={busy}>
                      View handoff
                    </Button>
                  </div>

                  {handoffRecord ? (
                    <div className="rounded-xl border border-line bg-panel-2 p-4 text-sm text-text">
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">Handoff record</div>
                      <div className="mt-2 space-y-1">
                        <div>Status: {handoffRecord.status}</div>
                        <div>Preview: {handoffRecord.previewUrl}</div>
                        <div>Theme: {handoffRecord.themeKey}</div>
                        <div>Updated: {formatDate(handoffRecord.updatedAt)}</div>
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
