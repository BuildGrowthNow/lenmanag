"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  Clock,
  Info,
  XCircle,
  Activity,
} from "lucide-react";

import type { PipelineEvent, PipelineEventStatus, PipelineEventType } from "@/lib/types";
import { cn } from "@/lib/utils";

// Event type to human-readable label mapping
const EVENT_LABELS: Record<PipelineEventType, string> = {
  lead_created: "Lead Created",
  lead_merged: "Lead Merged",
  extraction_started: "Extraction Started",
  extraction_progress: "Extraction Progress",
  extraction_completed: "Extraction Completed",
  extraction_failed: "Extraction Failed",
  analysis_started: "Analysis Started",
  analysis_completed: "Analysis Completed",
  analysis_failed: "Analysis Failed",
  brief_generation_started: "Brief Generation Started",
  brief_generated: "Brief Generated",
  brief_approved: "Brief Approved",
  brief_rejected: "Brief Rejected",
  site_generation_started: "Site Generation Started",
  site_generation_progress: "Site Generation Progress",
  site_variant_generated: "Variant Generated",
  site_generation_completed: "Site Generation Completed",
  site_generation_failed: "Site Generation Failed",
  qa_started: "QA Started",
  qa_passed: "QA Passed",
  qa_failed: "QA Failed",
  site_published: "Site Published",
  pipeline_error: "Pipeline Error",
  pipeline_paused: "Pipeline Paused",
  pipeline_resumed: "Pipeline Resumed",
};

// Status icon component
function StatusIcon({ status }: { status: PipelineEventStatus }) {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    case "error":
      return <XCircle className="h-4 w-4 text-rose-400" />;
    case "warning":
      return <AlertTriangle className="h-4 w-4 text-amber-400" />;
    case "info":
    default:
      return <Info className="h-4 w-4 text-blue-400" />;
  }
}

// Status badge styling
function statusBadgeClass(status: PipelineEventStatus): string {
  switch (status) {
    case "success":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
    case "error":
      return "border-rose-500/30 bg-rose-500/10 text-rose-300";
    case "warning":
      return "border-amber-500/30 bg-amber-500/10 text-amber-300";
    case "info":
    default:
      return "border-blue-500/30 bg-blue-500/10 text-blue-300";
  }
}

// Timeline dot styling
function timelineDotClass(status: PipelineEventStatus): string {
  switch (status) {
    case "success":
      return "bg-emerald-500";
    case "error":
      return "bg-rose-500";
    case "warning":
      return "bg-amber-500";
    case "info":
    default:
      return "bg-blue-500";
  }
}

// Format relative time
function formatRelativeTime(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// Format absolute time
function formatAbsoluteTime(isoTimestamp: string): string {
  return new Date(isoTimestamp).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Single event row
function EventRow({ event, isLast }: { event: PipelineEvent; isLast: boolean }) {
  // Auto-expand errors so they're immediately visible
  const isError = event.status === "error";
  const [expanded, setExpanded] = useState(isError);
  const hasDetail = event.detail || Object.keys(event.metadata).length > 0;

  return (
    <div className="relative flex gap-3">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-[7px] top-6 h-[calc(100%-12px)] w-px bg-line" />
      )}

      {/* Timeline dot */}
      <div
        className={cn(
          "relative z-10 mt-1.5 h-3.5 w-3.5 shrink-0 rounded-full border-2 border-background",
          timelineDotClass(event.status)
        )}
      />

      {/* Event content */}
      <div className="flex-1 pb-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <StatusIcon status={event.status} />
            <span className="text-sm font-medium text-text">
              {EVENT_LABELS[event.eventType] || event.eventType}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted">
            <Clock className="h-3 w-3" />
            <span title={formatAbsoluteTime(event.timestamp)}>
              {formatRelativeTime(event.timestamp)}
            </span>
          </div>
        </div>

        <p className="mt-1 text-sm text-muted">{event.message}</p>

        {hasDetail && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-1.5 flex items-center gap-1 text-xs text-muted hover:text-text transition-colors"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-3 w-3" />
                Hide details
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" />
                Show details
              </>
            )}
          </button>
        )}

        {expanded && hasDetail && (
          <div className={cn(
            "mt-2 rounded-lg border p-3 text-xs",
            isError
              ? "border-rose-500/30 bg-rose-500/5"
              : "border-line bg-panel"
          )}>
            {event.detail && (
              <pre className={cn(
                "whitespace-pre-wrap font-mono text-xs mb-2",
                isError ? "text-rose-300" : "text-muted"
              )}>{event.detail}</pre>
            )}
            {Object.keys(event.metadata).length > 0 && (
              <div className="space-y-1">
                {Object.entries(event.metadata).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-2">
                    <span className="text-muted">{key}:</span>
                    <span className="text-text font-mono">
                      {typeof value === "object" ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {event.jobId && (
              <div className="mt-2 pt-2 border-t border-line flex justify-between">
                <span className="text-muted">Job ID:</span>
                <span className="text-text font-mono">{event.jobId.slice(0, 12)}</span>
              </div>
            )}
            {event.durationMs && (
              <div className="flex justify-between">
                <span className="text-muted">Duration:</span>
                <span className="text-text">{(event.durationMs / 1000).toFixed(1)}s</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Main component
export function PipelineActivityLog({
  events,
  className,
  defaultExpanded = false,
  maxCollapsedEvents = 5,
}: {
  events: PipelineEvent[];
  className?: string;
  defaultExpanded?: boolean;
  maxCollapsedEvents?: number;
}) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);
  const [showAll, setShowAll] = useState(false);

  if (!events || events.length === 0) {
    return (
      <div className={cn("rounded-2xl border border-line bg-panel-2 p-4", className)}>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Activity className="h-4 w-4" />
          <span>No activity recorded yet</span>
        </div>
      </div>
    );
  }

  const displayedEvents = showAll ? events : events.slice(0, maxCollapsedEvents);
  const hasMore = events.length > maxCollapsedEvents;

  // Summary of recent activity
  const latestEvent = events[0];
  const successCount = events.filter((e) => e.status === "success").length;
  const errorCount = events.filter((e) => e.status === "error").length;

  return (
    <div className={cn("rounded-2xl border border-line bg-panel-2", className)}>
      {/* Header / Toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between gap-3 p-4 text-left hover:bg-white/2 transition-colors rounded-2xl"
      >
        <div className="flex items-center gap-3">
          <Activity className="h-4 w-4 text-accent" />
          <div>
            <div className="text-sm font-medium text-text">Pipeline Activity</div>
            <div className="mt-0.5 text-xs text-muted">
              {events.length} event{events.length !== 1 ? "s" : ""} ·{" "}
              Latest: {EVENT_LABELS[latestEvent.eventType] || latestEvent.eventType}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Quick stats */}
          <div className="hidden sm:flex items-center gap-2">
            {successCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                {successCount}
              </span>
            )}
            {errorCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-rose-400">
                <XCircle className="h-3 w-3" />
                {errorCount}
              </span>
            )}
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-muted" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted" />
          )}
        </div>
      </button>

      {/* Event list */}
      {isOpen && (
        <div className="border-t border-line px-4 pt-4 pb-2">
          {displayedEvents.map((event, index) => (
            <EventRow
              key={event.id}
              event={event}
              isLast={index === displayedEvents.length - 1}
            />
          ))}

          {/* Show more / Show less */}
          {hasMore && (
            <div className="pt-2 pb-2">
              <button
                type="button"
                onClick={() => setShowAll(!showAll)}
                className="text-xs text-accent hover:underline"
              >
                {showAll
                  ? "Show less"
                  : `Show ${events.length - maxCollapsedEvents} more events`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
