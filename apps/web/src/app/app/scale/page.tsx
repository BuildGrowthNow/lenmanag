"use client";

import { useEffect, useState } from "react";

import { QueueHealthPanel } from "@/components/queue-health-panel";
import { ErrorState } from "@/components/state/error-state";
import { LoadingState } from "@/components/state/loading-state";
import { PageFrame } from "@/components/shell/page-frame";
import { request } from "@/lib/api/client";
import type { JobQueueHealthResponse } from "@/lib/types";

export default function ScalePage() {
  const [health, setHealth] = useState<JobQueueHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void request<JobQueueHealthResponse>("/api/jobs/health")
      .then((result) => {
        if (active) setHealth(result);
      })
      .catch((cause) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Failed to load queue health.");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <PageFrame
      eyebrow="Ops"
      title="Queue health"
      description="Monitor Celery job queue health, retry failed jobs, and kill stalled crawls. Auto-refresh every 30 seconds is available."
    >
      {error ? (
        <ErrorState title="Failed to load queue health" description={error} />
      ) : health ? (
        <QueueHealthPanel health={health} />
      ) : (
        <LoadingState label="Loading queue health…" />
      )}
    </PageFrame>
  );
}
