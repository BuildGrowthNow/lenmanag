"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { refineSite, submitRefinementPrompt } from "@/lib/api/sites";

export function RefinementPromptInput({ siteId }: { siteId: string }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"refine" | "regenerate">("refine");

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
    try {
      if (mode === "refine") {
        await refineSite(siteId, value);
      } else {
        await submitRefinementPrompt(siteId, value, true);
      }
      setPrompt("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setIsLoading(false);
    }
  }

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
        {mode === "regenerate" && (
          <span className="text-amber-400/80">Starts from scratch — existing design will be replaced</span>
        )}
        {error ? <span className="text-rose-500">{error}</span> : null}
      </div>
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
