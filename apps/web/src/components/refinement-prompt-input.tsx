"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { refineSite, submitRefinementPrompt } from "@/lib/api/sites";
import { getJob } from "@/lib/api/jobs";

type JobStatus = "queued" | "running" | "completed" | "failed";

export function RefinementPromptInput({ siteId }: { siteId: string }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"refine" | "regenerate">("refine");
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobStep, setJobStep] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollJob = useCallback(
    (jobId: string) => {
      const tick = async () => {
        const result = await getJob(jobId);
        if (!result) return;
        const status = result.job.status as JobStatus;
        setJobStatus(status);
        setJobStep(result.job.step ?? null);
        if (status === "completed") {
          stopPolling();
          setIsLoading(false);
          router.refresh();
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
    [router, stopPolling]
  );

  useEffect(() => stopPolling, [stopPolling]);

  async function handleSubmit() {
    const value = prompt.trim();
    if (!value) {
      setError("Prompt cannot be empty");
      return;
    }
    if (value.length > 500) {
      setError("Prompt must be less than 500 characters");
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

  const statusLabel =
    jobStatus === "queued"
      ? "Queued…"
      : jobStatus === "running"
      ? jobStep ?? "Running…"
      : jobStatus === "completed"
      ? "Done — refreshing…"
      : null;

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
        maxLength={500}
        disabled={isLoading}
        className="w-full resize-none rounded-lg border border-line bg-panel px-4 py-3 text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
        rows={4}
      />
      <div className="mt-2 flex items-center justify-between text-xs text-muted">
        <span>{prompt.length}/500</span>
        {mode === "regenerate" && !isLoading && (
          <span className="text-amber-400/80">Starts from scratch — existing design will be replaced</span>
        )}
        {error ? <span className="text-rose-500">{error}</span> : null}
      </div>
      {statusLabel ? (
        <div className="mt-3 flex items-center gap-2 text-sm text-sky-300">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-sky-400" />
          {statusLabel}
        </div>
      ) : null}
      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={isLoading || !prompt.trim()}
        className="mt-4 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {isLoading
          ? "Processing…"
          : mode === "refine"
          ? "Apply refinement"
          : "Regenerate site"}
      </button>
    </div>
  );
}
