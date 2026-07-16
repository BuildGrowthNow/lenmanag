"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { retryJob, getQueueHealth } from "@/lib/api/jobs";
import type { JobQueueHealthItem, JobQueueHealthResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

function statusTone(status: string) {
  if (status === "running") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "queued") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

function fmt(n: number) {
  return n.toLocaleString();
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

type JobListProps = {
  title: string;
  description: string;
  jobs: JobQueueHealthItem[];
  reasons: Record<string, string>;
  onReasonChange: (jobId: string, value: string) => void;
  onRetry: (jobId: string) => void;
  busyJob: string | null;
  actionLabel?: string;
};

function JobList({ title, description, jobs, reasons, onReasonChange, onRetry, busyJob, actionLabel = "Retry job" }: JobListProps) {
  if (!jobs.length) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {jobs.map((job) => (
          <div key={job.id} className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-text">{job.jobType}</div>
                <div className="mt-0.5 font-mono text-xs text-muted">ID: {job.id.slice(0, 16)}…</div>
                <div className="text-xs text-muted">Updated {relativeTime(job.updatedAt)}</div>
              </div>
              <Badge className={statusTone(job.status)}>{job.status}</Badge>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-2">
              <div>Step: {job.step || "Waiting"}</div>
              <div>Progress: {job.progress}%</div>
              <div>Retry count: {job.retryCount}</div>
              <div>Lead IDs: {job.leadIds.join(", ") || "n/a"}</div>
            </div>
            {job.errorMessage && (
              <div className="mt-2 rounded-xl bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                {job.errorMessage}
              </div>
            )}
            <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
              <Input
                value={reasons[job.id] ?? ""}
                placeholder="Retry reason (optional)"
                onChange={(e) => onReasonChange(job.id, e.target.value)}
              />
              <Button
                type="button"
                onClick={() => onRetry(job.id)}
                disabled={busyJob === job.id}
              >
                {busyJob === job.id ? "Retrying…" : actionLabel}
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

type QueueHealthPanelProps = {
  health: JobQueueHealthResponse;
};

export function QueueHealthPanel({ health: initialHealth }: QueueHealthPanelProps) {
  const router = useRouter();
  const [health, setHealth] = useState(initialHealth);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busyJob, setBusyJob] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const doRefresh = useCallback(async () => {
    try {
      const fresh = await getQueueHealth();
      setHealth(fresh);
      setLastRefreshed(new Date());
    } catch {
      // silent — keep showing stale data
    }
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => void doRefresh(), 30_000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, doRefresh]);

  function updateReason(jobId: string, value: string) {
    setReasons((prev) => ({ ...prev, [jobId]: value }));
  }

  async function handleRetry(jobId: string) {
    setBusyJob(jobId);
    setFeedback(null);
    try {
      await retryJob(jobId, { reason: reasons[jobId] || "manual_retry_from_queue_health" });
      setFeedback({ type: "ok", text: `Retried job ${jobId.slice(0, 8)}…` });
      router.refresh();
      await doRefresh();
    } catch (error) {
      setFeedback({ type: "err", text: error instanceof Error ? error.message : "Retry failed." });
    } finally {
      setBusyJob(null);
    }
  }

  const byTypeEntries = Object.entries(health.byType).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      {/* Header controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="text-sm text-muted">
            {lastRefreshed
              ? `Updated ${relativeTime(lastRefreshed.toISOString())}`
              : "Server-rendered snapshot"}
          </div>
          {autoRefresh && (
            <Badge className="border-emerald-500/40 bg-emerald-500/10 text-emerald-200 text-xs">
              Auto-refresh on
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => void doRefresh()}
            className="rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted transition-colors hover:text-text"
          >
            Refresh now
          </button>
          <button
            onClick={() => setAutoRefresh((v) => !v)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs transition-colors",
              autoRefresh
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
                : "border-line bg-panel text-muted hover:text-text"
            )}
          >
            {autoRefresh ? "Auto-refresh: on" : "Auto-refresh: off"}
          </button>
        </div>
      </div>

      {/* Health strip */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Queued", value: health.queuedJobs, tone: "" },
          { label: "Running", value: health.runningJobs, tone: "" },
          { label: "Failed", value: health.failedJobs, tone: health.failedJobs > 0 ? "text-rose-400" : "" },
          { label: "Stalled", value: health.stalledJobs, tone: health.stalledJobs > 0 ? "text-amber-400" : "" },
        ].map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className={cn("text-3xl", card.tone)}>
                {fmt(card.value)}
              </CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      {/* Feedback notice */}
      {feedback && (
        <div
          className={cn(
            "rounded-2xl border px-4 py-3 text-sm",
            feedback.type === "ok"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              : "border-rose-500/30 bg-rose-500/10 text-rose-200"
          )}
        >
          {feedback.text}
        </div>
      )}

      {/* Failed jobs */}
      <JobList
        title="Failed jobs"
        description="Jobs that exited with an error. Add a reason note to keep the audit trail readable."
        jobs={health.failedItems}
        reasons={reasons}
        onReasonChange={updateReason}
        onRetry={handleRetry}
        busyJob={busyJob}
      />

      {/* Stalled jobs */}
      <JobList
        title="Stalled jobs"
        description="Jobs running longer than 30 minutes. Kill and retry after inspecting the error."
        jobs={health.stalledItems}
        reasons={reasons}
        onReasonChange={updateReason}
        onRetry={handleRetry}
        busyJob={busyJob}
        actionLabel="Kill & retry"
      />

      {/* Job type breakdown — collapsed by default */}
      <details>
        <summary className="flex cursor-pointer list-none items-center gap-2 rounded-2xl border border-line bg-panel px-5 py-3 text-sm font-medium text-text hover:bg-panel-2">
          <span className="mr-auto">By job type</span>
          <span className="text-xs text-muted">{byTypeEntries.length} type{byTypeEntries.length !== 1 ? "s" : ""} →</span>
        </summary>
        <div className="mt-3">
          <Card>
            <CardContent className="overflow-x-auto p-0">
              {byTypeEntries.length ? (
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-xs uppercase tracking-[0.18em] text-muted">
                      <th className="px-4 py-2.5">Job type</th>
                      <th className="px-4 py-2.5 text-right">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byTypeEntries.map(([type, count]) => (
                      <tr key={type} className="border-t border-line/50">
                        <td className="px-4 py-3 font-medium text-text">{type}</td>
                        <td className="px-4 py-3 text-right text-muted">{fmt(count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="px-4 py-6 text-sm text-muted">No jobs recorded yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </details>

      {/* Backlog snapshot */}
      <Card>
        <CardHeader>
          <CardTitle>Backlog</CardTitle>
          <CardDescription>Total queue depth across queued and stalled jobs.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
            <div className="text-xs text-muted">Backlog size</div>
            <div className="mt-0.5 text-2xl font-semibold text-text">{fmt(health.backlogJobs)}</div>
          </div>
          <div className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
            <div className="text-xs text-muted">Total tracked</div>
            <div className="mt-0.5 text-2xl font-semibold text-text">{fmt(health.totalJobs)}</div>
          </div>
          <div className="rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
            <div className="text-xs text-muted">Completed</div>
            <div className="mt-0.5 text-2xl font-semibold text-text">{fmt(health.completedJobs)}</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
