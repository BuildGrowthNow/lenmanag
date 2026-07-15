"use client";

import { useState } from "react";
import { submitRefinementPrompt } from "@/lib/api/sites";

export function RefinementPromptInput({ siteId }: { siteId: string }) {
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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
      await submitRefinementPrompt(siteId, value);
      setPrompt("");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to submit refinement prompt");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-line bg-panel-2 p-6">
      <label className="mb-2 block text-sm font-semibold text-text">
        Redesign Refinement Prompt
      </label>
      <textarea
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder='E.g., "Make this feel more premium and modern while keeping the core product story intact."'
        maxLength={500}
        disabled={isLoading}
        className="w-full resize-none rounded-lg border border-line bg-panel px-4 py-3 text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
        rows={4}
      />
      <div className="mt-2 flex items-center justify-between text-xs text-muted">
        <span>{prompt.length}/500</span>
        {error ? <span className="text-rose-500">{error}</span> : null}
      </div>
      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={isLoading || !prompt.trim()}
        className="mt-4 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {isLoading ? "Processing..." : "Submit Refinement"}
      </button>
    </div>
  );
}
