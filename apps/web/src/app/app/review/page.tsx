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
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let active = true;
    setQueue(null);
    setError(null);
    getSiteReviewQueue({ limit: 25, offset })
      .then((value) => { if (active) setQueue(value); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : "Failed to load review queue."); });
    return () => { active = false; };
  }, [offset]);

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
        <>
          <SiteReviewQueue queue={queue} />
          <div className="flex items-center justify-between gap-4 py-6">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))} className="disabled:opacity-40">Previous</button>
            <span>{queue.pagination.total === 0 ? "0" : `${offset + 1}–${Math.min(offset + 25, queue.pagination.total)}`} of {queue.pagination.total} websites</span>
            <button disabled={offset + 25 >= queue.pagination.total} onClick={() => setOffset(offset + 25)} className="disabled:opacity-40">Next</button>
          </div>
        </>
      )}
    </PageFrame>
  );
}
