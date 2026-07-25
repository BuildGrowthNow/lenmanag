"use client";

import Image from "next/image";
import Link from "next/link";
import { ExternalLink, SkipForward } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { approveSiteReview, patchSiteReview, refineSite, submitRefinementPrompt } from "@/lib/api/sites";
import { getJob } from "@/lib/api/jobs";
import type { SiteReviewQueueItem, SiteReviewQueueResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

function readinessTone(status: string) {
  if (status === "published" || status === "ready_to_publish" || status === "approved")
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (status === "ready_for_review" || status === "warned")
    return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  if (status === "blocked" || status === "fail")
    return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

// ── Single review card ─────────────────────────────────────────────────────

type ReviewCardProps = {
  item: SiteReviewQueueItem;
  onApproved: () => void;
  onRegenerated: () => void;
  onSkipped: () => void;
};

type JobStatus = "queued" | "running" | "completed" | "failed";

function ReviewCard({ item, onApproved, onRegenerated, onSkipped }: ReviewCardProps) {
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobStep, setJobStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const VARIANT_LABELS: Record<string, string> = {
    html_v1: "HTML v1",
    html_v2: "HTML v2",
    html_v3: "HTML v3",
    nextjs: "Next.js",
  };
  const companyName =
    item.sourceAttribution?.companyName ||
    item.sourceAttribution?.normalizedDomain ||
    item.leadId.slice(0, 8);
  const variantLabel = item.variantType ? (VARIANT_LABELS[item.variantType] ?? item.variantType) : null;
  const displayTitle = companyName + (variantLabel ? ` · ${variantLabel}` : "");
  const domain = item.sourceAttribution?.normalizedDomain ?? "";
  const screenshotUrl = item.screenshotRefs?.[0]?.url ?? null;

  const flaggedIssues = [
    ...item.missingRequirements,
    ...item.reviewRubric.filter((r) => r.status !== "pass").map((r) => r.notes || r.label),
  ].filter(Boolean);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const pollJob = useCallback(
    (jobId: string, onDone: () => void) => {
      const tick = async () => {
        const result = await getJob(jobId);
        if (!result) return;
        const status = result.job.status as JobStatus;
        setJobStatus(status);
        setJobStep(result.job.step ?? null);
        if (status === "completed") {
          stopPolling();
          setBusy(false);
          onDone();
        } else if (status === "failed") {
          stopPolling();
          setBusy(false);
          setError(result.job.errorMessage ?? "Job failed");
        } else {
          pollRef.current = setTimeout(tick, 3000);
        }
      };
      pollRef.current = setTimeout(tick, 2000);
    },
    [stopPolling]
  );

  async function handleApprove() {
    setBusy(true);
    setError(null);
    try {
      await patchSiteReview(item.siteId, { outcome: "pass", notes: null, blockedReason: null });
      await approveSiteReview(item.siteId);
      onApproved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed.");
      setBusy(false);
    }
  }

  async function handleRefine() {
    if (!prompt.trim()) return;
    setBusy(true);
    setError(null);
    setJobStatus("queued");
    setJobStep("Queued");
    try {
      const result = await refineSite(item.siteId, prompt.trim());
      setPrompt("");
      if (result.status === "completed") {
        setBusy(false);
        setJobStatus("completed");
        onRegenerated();
      } else {
        pollJob(result.jobId, onRegenerated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to queue refinement.");
      setBusy(false);
      setJobStatus(null);
    }
  }

  async function handleRegenerate() {
    setBusy(true);
    setError(null);
    setJobStatus("queued");
    setJobStep("Queued");
    try {
      const result = await submitRefinementPrompt(
        item.siteId,
        prompt.trim() || "Regenerate with fresh creative direction.",
        true,
      );
      setPrompt("");
      if (result.status === "completed") {
        setBusy(false);
        setJobStatus("completed");
        onRegenerated();
      } else {
        pollJob(result.jobId, onRegenerated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to queue regeneration.");
      setBusy(false);
      setJobStatus(null);
    }
  }

  const statusLabel =
    jobStatus === "queued"
      ? "Queued…"
      : jobStatus === "running"
      ? jobStep ?? "Refining…"
      : jobStatus === "completed"
      ? "Done — updating queue…"
      : null;

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col md:flex-row">
        {/* Thumbnail / preview area */}
        <div className="relative shrink-0 md:w-64">
          {screenshotUrl ? (
            <div className="relative h-48 w-full md:h-full md:min-h-48">
              <Image
                src={screenshotUrl}
                alt={`Preview of ${companyName}`}
                fill
                className="object-cover object-top"
                unoptimized
              />
            </div>
          ) : (
            <Link href={item.previewUrl} target="_blank" className="block h-48 md:h-full md:min-h-48">
              <div className="flex h-full w-full items-center justify-center bg-panel-2 transition hover:bg-panel-1">
                <ExternalLink className="h-5 w-5 text-muted" />
              </div>
            </Link>
          )}
        </div>

        {/* Content */}
        <CardContent className="flex flex-1 flex-col gap-4 p-5">
          {/* Header */}
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-semibold text-text">{displayTitle}</div>
              {domain ? <div className="mt-0.5 text-xs text-muted">{domain}</div> : null}
              <div className="mt-1 text-xs text-muted">
                v{item.version} · {item.paletteMode} · {item.qualityScore}/100
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={readinessTone(item.readinessStatus)}>
                {item.readinessStatus.replace(/_/g, " ")}
              </Badge>
              <Button variant="secondary" size="sm">
                <Link href={item.previewUrl} target="_blank" className="flex items-center gap-1.5">
                  Preview
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </Button>
              <Button variant="ghost" size="sm">
                <Link href={`/app/leads/${item.leadId}`}>Open spec</Link>
              </Button>
              <Button variant="ghost" size="sm" onClick={onSkipped} disabled={busy}>
                <SkipForward className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {/* Flagged issues — only shown when present */}
          {flaggedIssues.length > 0 && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
              <div className="mb-2 text-xs uppercase tracking-[0.18em] text-amber-400/70">Issues</div>
              <ul className="space-y-1">
                {flaggedIssues.map((issue, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-amber-100">
                    <span className="mt-px text-amber-400">⚠</span>
                    <span>{issue}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Prompt + actions */}
          <div className="space-y-3">
            <Textarea
              rows={3}
              placeholder='Describe targeted changes to refine — e.g. "change the hero font to serif, make the CTA button larger"'
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={busy}
              className="resize-none text-sm"
            />
            {statusLabel ? (
              <div className="flex items-center gap-2 text-sm text-sky-300">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-sky-400" />
                {statusLabel}
              </div>
            ) : null}
            {error ? (
              <div className="rounded-xl border border-rose-500/30 px-3 py-2 text-sm text-rose-300">
                {error}
              </div>
            ) : null}
            <div className="flex flex-wrap items-center gap-2">
              <Button
                onClick={handleApprove}
                disabled={busy}
                className="border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
                variant="ghost"
              >
                {busy && jobStatus === null ? "Working…" : "Approve →"}
              </Button>
              <Button
                onClick={handleRefine}
                disabled={busy || !prompt.trim()}
                variant="ghost"
                className="border-sky-500/40 bg-sky-500/10 text-sky-200 hover:bg-sky-500/20"
              >
                {busy && jobStatus !== null ? "Refining…" : "Refine →"}
              </Button>
              <Button
                onClick={handleRegenerate}
                disabled={busy}
                variant="ghost"
                size="sm"
                className="text-xs text-muted hover:text-text"
              >
                Full regeneration
              </Button>
            </div>
          </div>
        </CardContent>
      </div>
    </Card>
  );
}

// ── Queue ──────────────────────────────────────────────────────────────────

type SiteReviewQueueProps = {
  queue: SiteReviewQueueResponse;
};

export function SiteReviewQueue({ queue }: SiteReviewQueueProps) {
  const [items, setItems] = useState<SiteReviewQueueItem[]>(queue.items);
  const [skipped, setSkipped] = useState<Set<string>>(new Set());

  const visible = items.filter((item) => !skipped.has(item.siteId));

  function removeItem(siteId: string) {
    setItems((prev) => prev.filter((i) => i.siteId !== siteId));
  }

  function skipItem(siteId: string) {
    setSkipped((prev) => new Set(prev).add(siteId));
  }

  const liveSummary = useMemo(() => ({
    ready: items.filter((i) => i.readinessStatus === "ready_to_publish").length,
    needsReview: items.filter((i) => i.readinessStatus === "needs_review").length,
    blocked: items.filter((i) => i.readinessStatus === "blocked").length,
    regenerationBacklog: items.filter((i) => i.reviewState === "blocked").length,
  }), [items]);

  return (
    <div className="space-y-6">
      {/* Summary strip */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Ready for automation", value: liveSummary.ready, color: "emerald" },
          { label: "Needs review", value: liveSummary.needsReview, color: "amber" },
          { label: "Blocked", value: liveSummary.blocked, color: "rose" },
          { label: "Regeneration backlog", value: liveSummary.regenerationBacklog, color: "sky" },
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

      {/* Queue items */}
      {visible.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line p-10 text-center">
          <div className="text-lg font-medium text-text">Queue is empty</div>
          <div className="mt-2 text-sm text-muted">
            All sites have been reviewed or are not yet ready for QA.
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-sm text-muted">
            {visible.length} site{visible.length !== 1 ? "s" : ""} pending review
            {skipped.size > 0 ? ` · ${skipped.size} skipped` : ""}
          </div>
          {visible.map((item) => (
            <ReviewCard
              key={item.siteId}
              item={item}
              onApproved={() => removeItem(item.siteId)}
              onRegenerated={() => removeItem(item.siteId)}
              onSkipped={() => skipItem(item.siteId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
