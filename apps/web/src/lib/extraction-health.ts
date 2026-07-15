import type { ExtractionSnapshot, ExtractionStatus } from "@/lib/types";

export const EXTRACTION_STALE_THRESHOLD_HOURS = 72;

export type ExtractionHealth = {
  hasExtraction: boolean;
  crawlStatus: ExtractionStatus;
  updatedAt: string | null;
  version: number;
  ageHours: number | null;
  isStale: boolean;
  isRunning: boolean;
  isFailed: boolean;
  blockReason: string | null;
};

function hoursSince(dateString: string | null): number | null {
  if (!dateString) {
    return null;
  }
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  const diffMs = Date.now() - date.getTime();
  return Math.floor(diffMs / (1000 * 60 * 60));
}

export function formatDateTime(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleString();
}

export function extractionAgeLabel(ageHours: number | null): string | null {
  if (typeof ageHours !== "number") {
    return null;
  }
  if (ageHours < 1) {
    return "<1 hour ago";
  }
  if (ageHours < 24) {
    return `~${ageHours}h ago`;
  }
  const days = Math.floor(ageHours / 24);
  return `~${days}d ago`;
}

export function evaluateExtractionHealth(
  snapshot: Pick<ExtractionSnapshot, "version" | "updatedAt" | "crawlStatus"> | null
): ExtractionHealth {
  const hasExtraction = Boolean(snapshot && snapshot.version > 0);
  const crawlStatus: ExtractionStatus = snapshot?.crawlStatus ?? "idle";
  const updatedAt = snapshot?.updatedAt ?? null;
  const version = snapshot?.version ?? 0;
  const ageHours = hoursSince(updatedAt);
  const isRunning = crawlStatus === "running" || crawlStatus === "queued";
  const isFailed = crawlStatus === "failed";
  const isStale = hasExtraction && typeof ageHours === "number" && ageHours >= EXTRACTION_STALE_THRESHOLD_HOURS;

  let blockReason: string | null = null;
  if (!hasExtraction) {
    blockReason = "Run an extraction before generating or editing the brief.";
  } else if (isRunning) {
    blockReason = "Extraction refresh is still running. Wait for it to finish before editing.";
  } else if (isFailed) {
    blockReason = "Latest extraction attempt failed. Refresh before editing the brief.";
  } else if (isStale) {
    blockReason = `Extraction snapshot is older than ${EXTRACTION_STALE_THRESHOLD_HOURS} hours. Refresh before editing.`;
  }

  return {
    hasExtraction,
    crawlStatus,
    updatedAt,
    version,
    ageHours,
    isStale,
    isRunning,
    isFailed,
    blockReason
  };
}
