"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/shell/page-frame";
import { SiteReviewQueue } from "@/components/site-review-queue";
import { LoadingState } from "@/components/state/loading-state";
import { ErrorState } from "@/components/state/error-state";
import { getSiteReviewQueue } from "@/lib/api/sites";
import type { SiteReviewQueueResponse } from "@/lib/types";

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<SiteReviewQueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSiteReviewQueue({ limit: 25, offset: 0 })
      .then(setQueue)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load review queue."));
  }, []);

  return (
    <PageFrame
      eyebrow="QA"
      title="Browser review queue"
      description="Screenshot-backed review workflow with diversity checks, regeneration controls, and automation handoff visibility."
    >
      {error ? (
        <ErrorState title="Failed to load review queue" description={error} />
      ) : queue === null ? (
        <LoadingState label="Loading review queue…" />
      ) : (
        <SiteReviewQueue queue={queue} />
      )}
    </PageFrame>
  );
}
