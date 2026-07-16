"use client";

import Link from "next/link";
import { ExternalLink, ChevronLeft, ChevronRight, SkipForward } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  approveSiteReview,
  getSiteReviewRecord,
  patchSiteReview,
  republishSite,
  submitSiteReview,
} from "@/lib/api/sites";
import type {
  SiteReviewChecklistItem,
  SiteReviewQueueItem,
  SiteReviewQueueResponse,
  SiteReviewRecord,
  SiteScreenshotMetadata,
  SiteQaStatus,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

// ── Helpers ────────────────────────────────────────────────────────────────

function statusTone(status: string) {
  if (["approved", "pass", "ready_to_publish"].includes(status))
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (["warn", "ready_for_review", "warned"].includes(status))
    return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  if (["blocked", "fail"].includes(status))
    return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function deriveChecklist(item: SiteReviewQueueItem): SiteReviewChecklistItem[] {
  return item.reviewRubric.map((check) => ({
    key: check.key,
    label: check.label,
    status: check.status,
    notes: check.notes,
    evidence: check.evidence ?? null,
  }));
}

function newScreenshot(label: string, url: string): SiteScreenshotMetadata {
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);
  return { id, label, url, capturedAt: new Date().toISOString(), width: null, height: null, contentHash: null, notes: null };
}

// ── Reject form modal (inline) ─────────────────────────────────────────────

type RejectFormProps = {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  busy: boolean;
};

function RejectForm({ onConfirm, onCancel, busy }: RejectFormProps) {
  const [reason, setReason] = useState("");
  return (
    <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/5 p-4 space-y-3">
      <div className="text-sm font-medium text-rose-300">Reject — regenerate</div>
      <Textarea
        rows={3}
        placeholder="Explain what needs to change before regeneration…"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="text-sm"
      />
      <div className="flex gap-2">
        <Button
          variant="ghost"
          onClick={onCancel}
          disabled={busy}
          className="flex-1"
        >
          Cancel
        </Button>
        <Button
          onClick={() => onConfirm(reason)}
          disabled={busy || !reason.trim()}
          className="flex-1 border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
          variant="ghost"
        >
          {busy ? "Queueing…" : "Reject & regenerate"}
        </Button>
      </div>
    </div>
  );
}

// ── Review workspace ───────────────────────────────────────────────────────

type ReviewWorkspaceProps = {
  item: SiteReviewQueueItem;
  onApproved: () => void;
  onRejected: () => void;
};

function ReviewWorkspace({ item, onApproved, onRejected }: ReviewWorkspaceProps) {
  const [reviewRecord, setReviewRecord] = useState<SiteReviewRecord | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [checklist, setChecklist] = useState<SiteReviewChecklistItem[]>([]);
  const [screenshots, setScreenshots] = useState<SiteScreenshotMetadata[]>([]);
  const [newShot, setNewShot] = useState({ label: "", url: "" });
  const [form, setForm] = useState({
    browserPreviewUrl: item.previewUrl,
    outcome: (item.qaStatus === "fail" ? "fail" : "warn") as SiteQaStatus,
    notes: "",
    blockedReason: "",
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [showRejectForm, setShowRejectForm] = useState(false);

  // Load existing review record on mount
  useState(() => {
    (async () => {
      try {
        const record = await getSiteReviewRecord(item.siteId);
        setReviewRecord(record);
        if (record) {
          setForm({
            browserPreviewUrl: record.browserPreviewUrl ?? item.previewUrl,
            outcome: record.outcome,
            notes: record.notes ?? "",
            blockedReason: record.blockedReason ?? "",
          });
          setChecklist(record.checklist.length ? record.checklist : deriveChecklist(item));
          setScreenshots(record.screenshots ?? []);
        } else {
          setChecklist(deriveChecklist(item));
        }
      } catch {
        setChecklist(deriveChecklist(item));
      } finally {
        setLoaded(true);
      }
    })();
  });

  function updateChecklist(key: string, field: "status" | "notes", value: string) {
    setChecklist((items) =>
      items.map((entry) => (entry.key === key ? { ...entry, [field]: value } : entry))
    );
  }

  async function saveReview() {
    setBusy(true);
    setMessage(null);
    const payload = {
      browserPreviewUrl: form.browserPreviewUrl || null,
      outcome: form.outcome,
      checklist,
      screenshots,
      notes: form.notes || null,
      blockedReason: form.blockedReason || null,
    };
    try {
      const record = reviewRecord
        ? await patchSiteReview(item.siteId, payload)
        : await submitSiteReview(item.siteId, payload);
      setReviewRecord(record);
      setMessage("Review saved.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleApprove() {
    setBusy(true);
    setMessage(null);
    try {
      await saveReview();
      await approveSiteReview(item.siteId);
      onApproved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Approval failed.");
      setBusy(false);
    }
  }

  async function handleReject(reason: string) {
    setBusy(true);
    setMessage(null);
    try {
      await patchSiteReview(item.siteId, {
        outcome: "fail",
        notes: reason || null,
        blockedReason: reason || null,
      });
      await republishSite(item.siteId);
      setShowRejectForm(false);
      onRejected();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Reject failed.");
      setBusy(false);
    }
  }

  if (!loaded) {
    return <div className="py-4 text-sm text-muted">Loading review record…</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        {/* Left: screenshot placeholder + issues */}
        <div className="space-y-3">
          <div className="flex h-48 items-center justify-center rounded-2xl border border-dashed border-line bg-panel-2">
            {item.screenshotCount > 0 ? (
              <span className="text-xs text-muted">{item.screenshotCount} screenshot(s) recorded</span>
            ) : (
              <span className="text-xs text-muted">No screenshots yet</span>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" className="flex-1">
              <Link href={item.previewUrl} target="_blank" className="flex items-center gap-1.5">
                Preview site
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            </Button>
            <Button variant="secondary" className="flex-1">
              <Link href={`/app/sites/${item.siteId}`}>Open spec</Link>
            </Button>
          </div>
        </div>

        {/* Right: issues + details */}
        <div className="space-y-3">
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Issues flagged</div>
            <div className="mt-3 space-y-2">
              {item.missingRequirements.length ? (
                item.missingRequirements.map((req) => (
                  <div key={req} className="flex items-start gap-2 text-sm">
                    <span className="text-amber-400">⚠</span>
                    <span className="text-text">{req}</span>
                  </div>
                ))
              ) : (
                <span className="text-sm text-muted">No issues flagged</span>
              )}
              {item.reviewRubric
                .filter((c) => c.status !== "pass")
                .map((check) => (
                  <div key={check.key} className="flex items-start gap-2 text-sm">
                    <span className={check.status === "warn" ? "text-amber-400" : "text-rose-400"}>
                      {check.status === "warn" ? "⚠" : "✗"}
                    </span>
                    <span className="text-text">{check.label}</span>
                  </div>
                ))}
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-muted">Theme</div>
                <div className="mt-0.5 text-text">{item.themeKey}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Palette</div>
                <div className="mt-0.5 text-text">{item.paletteMode}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Quality score</div>
                <div className="mt-0.5 text-text">{item.qualityScore} / 100</div>
              </div>
              <div>
                <div className="text-xs text-muted">QA status</div>
                <div className="mt-0.5">
                  <Badge className={statusTone(item.qaStatus)}>{item.qaStatus}</Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reviewer form */}
      <div className="rounded-2xl border border-line bg-panel p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            <span className="text-xs uppercase tracking-[0.18em] text-muted">Browser preview URL</span>
            <Input
              className="mt-2"
              value={form.browserPreviewUrl}
              onChange={(e) => setForm((c) => ({ ...c, browserPreviewUrl: e.target.value }))}
            />
          </label>
          <label className="text-sm">
            <span className="text-xs uppercase tracking-[0.18em] text-muted">Outcome</span>
            <select
              className="mt-2 h-10 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text"
              value={form.outcome}
              onChange={(e) => setForm((c) => ({ ...c, outcome: e.target.value as SiteQaStatus }))}
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
            rows={2}
            value={form.notes}
            onChange={(e) => setForm((c) => ({ ...c, notes: e.target.value }))}
            placeholder="Reviewer notes"
          />
        </label>

        {checklist.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Checklist</div>
            <div className="mt-2 space-y-2">
              {checklist.map((entry) => (
                <div key={entry.key} className="rounded-xl border border-line bg-panel-2 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-medium text-text">{entry.label}</span>
                    <select
                      className="ml-auto rounded-xl border border-line bg-panel px-2 py-1 text-xs"
                      value={entry.status}
                      onChange={(e) => updateChecklist(entry.key, "status", e.target.value)}
                    >
                      <option value="pass">pass</option>
                      <option value="warn">warn</option>
                      <option value="fail">fail</option>
                    </select>
                  </div>
                  <Textarea
                    className="mt-2 text-sm"
                    rows={1}
                    value={entry.notes}
                    onChange={(e) => updateChecklist(entry.key, "notes", e.target.value)}
                    placeholder="Add notes"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Screenshots */}
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Screenshots</div>
          <div className="mt-2 space-y-2">
            {screenshots.map((shot) => (
              <div key={shot.id} className="flex items-center gap-3 rounded-xl border border-line bg-panel-2 p-3 text-sm">
                <div className="flex-1">
                  <div className="font-medium text-text">{shot.label}</div>
                  <div className="text-xs text-muted">{shot.url}</div>
                </div>
                <Button type="button" variant="ghost" onClick={() => setScreenshots((s) => s.filter((x) => x.id !== shot.id))}>
                  Remove
                </Button>
              </div>
            ))}
            <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
              <Input
                placeholder="Label"
                value={newShot.label}
                onChange={(e) => setNewShot((c) => ({ ...c, label: e.target.value }))}
              />
              <Input
                placeholder="https://…"
                value={newShot.url}
                onChange={(e) => setNewShot((c) => ({ ...c, url: e.target.value }))}
              />
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  if (!newShot.label.trim() || !newShot.url.trim()) return;
                  setScreenshots((s) => [...s, newScreenshot(newShot.label.trim(), newShot.url.trim())]);
                  setNewShot({ label: "", url: "" });
                }}
              >
                Add
              </Button>
            </div>
          </div>
        </div>

        {message ? (
          <div className={cn("rounded-xl border px-3 py-2 text-sm", message.toLowerCase().includes("fail") || message.toLowerCase().includes("error") ? "border-rose-500/30 text-rose-300" : "border-emerald-500/30 text-emerald-300")}>
            {message}
          </div>
        ) : null}

        {showRejectForm ? (
          <RejectForm
            onConfirm={handleReject}
            onCancel={() => setShowRejectForm(false)}
            busy={busy}
          />
        ) : (
          <div className="flex flex-wrap gap-2 pt-2">
            <Button onClick={saveReview} disabled={busy}>
              {busy ? "Saving…" : "Save review"}
            </Button>
            <Button variant="ghost" onClick={() => setShowRejectForm(true)} disabled={busy}>
              Reject — regenerate
            </Button>
            <Button onClick={handleApprove} disabled={busy} className="border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20" variant="ghost">
              {busy ? "Approving…" : "Approve →"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

type SiteReviewQueueProps = {
  queue: SiteReviewQueueResponse;
};

export function SiteReviewQueue({ queue }: SiteReviewQueueProps) {
  const router = useRouter();
  const [items, setItems] = useState<SiteReviewQueueItem[]>(queue.items);
  const [index, setIndex] = useState(0);
  const [skipped, setSkipped] = useState<string[]>([]);

  const pendingItems = items.filter((item) => !skipped.includes(item.siteId));
  const current = pendingItems[index] ?? null;
  const total = pendingItems.length;

  function advance() {
    if (index < total - 1) {
      setIndex((i) => i + 1);
    } else {
      setIndex(0);
    }
  }

  function handleApproved() {
    setItems((prev) => prev.filter((item) => item.siteId !== current?.siteId));
    router.refresh();
  }

  function handleRejected() {
    if (current) setSkipped((s) => [...s, current.siteId]);
    advance();
    router.refresh();
  }

  function handleSkip() {
    if (!current) return;
    setSkipped((s) => [...s, current.siteId]);
    advance();
  }

  return (
    <div className="space-y-6">
      {/* Automation summary + diversity */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Ready for automation", value: queue.automationSummary.ready, color: "emerald" },
          { label: "Needs review", value: queue.automationSummary.needsReview, color: "amber" },
          { label: "Blocked", value: queue.automationSummary.blocked, color: "rose" },
          { label: "Regeneration backlog", value: queue.automationSummary.regenerationBacklog, color: "sky" },
        ].map((card) => (
          <div
            key={card.label}
            className={`rounded-2xl border border-${card.color}-500/20 bg-${card.color}-500/5 px-4 py-3`}
          >
            <div className="text-xs uppercase tracking-[0.18em] text-muted">{card.label}</div>
            <div className={`mt-1 text-2xl font-semibold text-${card.color}-300`}>
              {card.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Batch diversity (collapsed) */}
      <details>
        <summary className="flex cursor-pointer items-center gap-2 rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm text-text hover:bg-white/5">
          <span className="font-medium">Batch diversity ▾</span>
        </summary>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          {(
            [
              ["Themes", queue.themeDiversity],
              ["Palette modes", queue.paletteDiversity],
              ["Motion presets", queue.motionDiversity],
              ["Spacing styles", queue.spacingDiversity],
            ] as Array<[string, Record<string, number>]>
          ).map(([label, dist]) => (
            <div key={label} className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">{label}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(dist).length ? (
                  Object.entries(dist).map(([key, count]) => (
                    <Badge key={key} className="border-line bg-panel text-sm">
                      {key}: {count}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted">No data yet.</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </details>

      {/* Queue */}
      {total === 0 ? (
        <div className="rounded-2xl border border-dashed border-line p-10 text-center">
          <div className="text-lg font-medium text-text">Queue is empty</div>
          <div className="mt-2 text-sm text-muted">
            All sites have been reviewed or are not ready for QA yet.
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Progress header */}
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm text-muted">
              {total} site{total !== 1 ? "s" : ""} pending review
              {skipped.length > 0 ? ` · ${skipped.length} skipped` : ""}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                disabled={index <= 0 || total <= 1}
                onClick={() => setIndex((i) => Math.max(0, i - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="min-w-16 text-center text-xs uppercase tracking-[0.2em] text-muted">
                {index + 1} / {total}
              </span>
              <Button
                variant="ghost"
                disabled={index >= total - 1}
                onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {current ? (
            <Card key={current.siteId}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>{current.leadId}</CardTitle>
                    <CardDescription>
                      Preview v{current.version} · Theme: {current.themeKey}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={statusTone(current.reviewState)}>
                      {current.reviewState.replace(/_/g, " ")}
                    </Badge>
                    <Badge className={statusTone(current.qaStatus)}>{current.qaStatus}</Badge>
                    <Badge className={statusTone(current.publishApprovalState)}>
                      {current.publishApprovalState}
                    </Badge>
                    <Button variant="ghost" onClick={handleSkip}>
                      <SkipForward className="mr-1.5 h-3.5 w-3.5" />
                      Skip
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ReviewWorkspace
                  item={current}
                  onApproved={handleApproved}
                  onRejected={handleRejected}
                />
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </div>
  );
}
