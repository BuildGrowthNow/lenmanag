"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { refineSite, submitRefinementPrompt, getSiteLatestJob } from "@/lib/api/sites";
import { CheckCircle2, Clock, XCircle, Loader2 } from "lucide-react";

type JobStatus = "queued" | "running" | "completed" | "failed";

export function RefinementPromptInput({ siteId }: { siteId: string }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"refine" | "regenerate">("refine");
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobStep, setJobStep] = useState<string | null>(null);
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollJob = useCallback(
    (_jobId: string) => {
      const tick = async () => {
        const result = await getSiteLatestJob(siteId);
        if (!result) {
          pollRef.current = setTimeout(tick, 3000);
          return;
        }
        const status = result.job.status as JobStatus;
        setJobStatus(status);
        setJobStep(result.job.step ?? null);
        if (status === "completed") {
          stopPolling();
          setIsLoading(false);
          setTimeout(() => {
            router.refresh();
          }, 1000);
        } else if (status === "failed") {
          stopPolling();
          setIsLoading(false);
          setError(result.job.errorMessage ?? "Job failed");
        } else {
          pollRef.current = setTimeout(tick, 3000);
        }
      };
      pollRef.current = setTimeout(tick, 2000);
    },
    [siteId, router, stopPolling]
  );

  // Check for existing active job on mount
  useEffect(() => {
    if (initialCheckDone) return;

    async function checkActiveJob() {
      try {
        const latestJob = await getSiteLatestJob(siteId);
        if (!latestJob) return;
        const status = latestJob.job.status as JobStatus;
        if (status === "queued" || status === "running") {
          setJobStatus(status);
          setJobStep(latestJob.job.step ?? null);
          setIsLoading(true);
          pollJob(latestJob.job.id);
        } else if (status === "completed") {
          // Job finished before or after a page refresh — show completed state briefly
          // then let the page stay in its current (already-refreshed) form view
          const finishedAt = latestJob.job.finishedAt ? new Date(latestJob.job.finishedAt).getTime() : 0;
          const ageMs = Date.now() - finishedAt;
          if (ageMs < 60_000) {
            // Completed within the last minute — show the green banner
            setJobStatus("completed");
          }
          // Older than 1 min: don't show anything, just show the form ready for next prompt
        } else if (status === "failed") {
          const finishedAt = latestJob.job.finishedAt ? new Date(latestJob.job.finishedAt).getTime() : 0;
          const ageMs = Date.now() - finishedAt;
          if (ageMs < 60_000) {
            setJobStatus("failed");
            setError(latestJob.job.errorMessage ?? "Last refinement failed");
          }
        }
      } catch (err) {
        console.error("Failed to check active job:", err);
      } finally {
        setInitialCheckDone(true);
      }
    }

    void checkActiveJob();
  }, [initialCheckDone, siteId, pollJob]);

  useEffect(() => stopPolling, [stopPolling]);

  async function handleSubmit() {
    const value = prompt.trim();
    if (!value) {
      setError("Prompt cannot be empty");
      return;
    }
    setIsLoading(true);
    setError(null);
    setJobStatus("queued");
    setJobStep("Queued");
    try {
      const result =
        mode === "refine"
          ? await refineSite(siteId, value)
          : await submitRefinementPrompt(siteId, value, true);
      setPrompt("");
      if (result.status === "completed") {
        setJobStatus("completed");
        setIsLoading(false);
        router.refresh();
      } else {
        pollJob(result.jobId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit");
      setIsLoading(false);
      setJobStatus(null);
      setJobStep(null);
    }
  }

  const isJobRunning = jobStatus === "queued" || jobStatus === "running";

  // If job is running, show centered status instead of form
  if (isJobRunning) {
    return (
      <div className="rounded-2xl border border-line bg-panel-2 p-8">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="flex items-center justify-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-sky-400" />
            <span className="text-lg font-medium text-text">
              {jobStatus === "queued" ? "Queued for refinement" : "Refining site..."}
            </span>
          </div>
          {jobStep && (
            <p className="text-sm text-muted max-w-md">
              {jobStep}
            </p>
          )}
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2">
            <Clock className="h-4 w-4 text-sky-400" />
            <span className="text-xs text-sky-300">
              You can leave this page - the job will continue in the background
            </span>
          </div>
        </div>
      </div>
    );
  }

  // If job just completed, show success message
  if (jobStatus === "completed" && !isLoading) {
    return (
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-8">
        <div className="flex flex-col items-center justify-center space-y-3 text-center">
          <CheckCircle2 className="h-6 w-6 text-emerald-400" />
          <p className="text-lg font-medium text-emerald-300">Refinement completed!</p>
          <p className="text-sm text-muted">Page will refresh automatically...</p>
        </div>
      </div>
    );
  }

  // Normal form view
  return (
    <div className="rounded-2xl border border-line bg-panel-2 p-6">
      <div className="mb-4 flex items-center justify-between">
        <label className="text-sm font-semibold text-text">
          {mode === "refine" ? "Refine site" : "Full regeneration"}
        </label>
        <button
          type="button"
          onClick={() => setMode(mode === "refine" ? "regenerate" : "refine")}
          className="text-xs text-muted underline-offset-2 hover:text-text hover:underline"
        >
          {mode === "refine" ? "Switch to full regeneration" : "Switch to targeted refinement"}
        </button>
      </div>
      <textarea
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder={
          mode === "refine"
            ? 'E.g. "Change the hero font to serif, make the CTA button larger, adjust spacing in the features section."'
            : 'E.g. "Make this feel more premium and modern while keeping the core product story intact."'
        }
        disabled={isLoading}
        className="w-full resize-none rounded-lg border border-line bg-panel px-4 py-3 text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed"
        rows={4}
      />
      <div className="mt-2 flex items-center justify-between text-xs text-muted">
        <span>{prompt.length} chars</span>
        {mode === "regenerate" && !isLoading && (
          <span className="text-amber-400/80">Starts from scratch — existing design will be replaced</span>
        )}
      </div>
      {error && (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2">
          <XCircle className="h-4 w-4 text-rose-400" />
          <span className="text-sm text-rose-300">{error}</span>
        </div>
      )}
      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={isLoading || !prompt.trim()}
        className="mt-4 w-full rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading
          ? "Submitting..."
          : mode === "refine"
          ? "Apply refinement"
          : "Regenerate site"}
      </button>
    </div>
  );
}
