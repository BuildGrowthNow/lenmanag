"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { retryJob } from "@/lib/api/jobs";
import type { JobQueueHealthItem, JobQueueHealthResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function statusTone(status: string) {
  if (status === "running") return "border-sky-500/40 bg-sky-500/10 text-sky-100";
  if (status === "queued") return "border-blue-500/40 bg-blue-500/10 text-blue-100";
  if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

type JobListProps = {
  title: string;
  description: string;
  jobs: JobQueueHealthItem[];
  reasons: Record<string, string>;
  onReasonChange: (jobId: string, value: string) => void;
  onRetry: (jobId: string) => void;
  busyJob: string | null;
};

function JobList({ title, description, jobs, reasons, onReasonChange, onRetry, busyJob }: JobListProps) {
  if (!jobs.length) {
    return null;
  }
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
                <div className="text-xs text-muted">Job ID: {job.id}</div>
                <div className="text-xs text-muted">Updated {formatDate(job.updatedAt)}</div>
              </div>
              <Badge className={statusTone(job.status)}>{job.status}</Badge>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-2">
              <div>Step: {job.step || "Waiting"}</div>
              <div>Progress: {job.progress}%</div>
              <div>Retry count: {job.retryCount}</div>
              <div>Lead IDs: {job.leadIds.join(", ") || "n/a"}</div>
              {job.errorMessage ? <div className="text-rose-200">Error: {job.errorMessage}</div> : null}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
              <Input
                value={reasons[job.id] ?? ""}
                placeholder="Retry reason"
                onChange={(event) => onReasonChange(job.id, event.target.value)}
              />
              <Button type="button" onClick={() => onRetry(job.id)} disabled={busyJob === job.id}>
                {busyJob === job.id ? "Retrying..." : "Retry job"}
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

export function QueueHealthPanel({ health }: QueueHealthPanelProps) {
  const router = useRouter();
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busyJob, setBusyJob] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const summaryCards = [
    { label: "Queued", value: health.queuedJobs },
    { label: "Running", value: health.runningJobs },
    { label: "Failed", value: health.failedJobs },
    { label: "Completed (24h)", value: health.completedJobs }
  ];

  const byTypeEntries = Object.entries(health.byType).sort((a, b) => b[1] - a[1]);

  function updateReason(jobId: string, value: string) {
    setReasons((current) => ({ ...current, [jobId]: value }));
  }

  async function handleRetry(jobId: string) {
    try {
      setBusyJob(jobId);
      setFeedback(null);
      await retryJob(jobId, { reason: reasons[jobId] || "manual_retry_from_queue_health" });
      setFeedback(`Retried job ${jobId.slice(0, 8)}.`);
      router.refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Retry failed.";
      setFeedback(message);
    } finally {
      setBusyJob(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
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
          <CardTitle>Queue distribution</CardTitle>
          <CardDescription>Breakdown by job type plus backlog health snapshot.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Backlog</div>
              <div className="mt-2 space-y-1 text-text">
                <div>Backlog size: {health.backlogJobs}</div>
                <div>Stalled jobs: {health.stalledJobs}</div>
                <div>Updated at: {formatDate(health.updatedAt)}</div>
              </div>
            </div>
            <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Job types</div>
              <div className="mt-2 space-y-1">
                {byTypeEntries.length ? (
                  byTypeEntries.map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between text-text">
                      <span className="text-sm font-medium">{type}</span>
                      <span className="text-xs text-muted">{count.toLocaleString()}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted">No jobs recorded yet.</div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {feedback ? <div className="rounded-2xl border border-line bg-panel p-4 text-sm text-text">{feedback}</div> : null}

      <JobList
        title="Stalled jobs"
        description="Jobs that have been running longer than 30 minutes. Retry after inspecting the reason."
        jobs={health.stalledItems}
        reasons={reasons}
        onReasonChange={updateReason}
        onRetry={handleRetry}
        busyJob={busyJob}
      />

      <JobList
        title="Failed jobs"
        description="Jobs that exited with an error. Retry with a short note so the audit trail stays readable."
        jobs={health.failedItems}
        reasons={reasons}
        onReasonChange={updateReason}
        onRetry={handleRetry}
        busyJob={busyJob}
      />
    </div>
  );
}
