"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageFrame } from "@/components/shell/page-frame";
import { getAnalyticsDashboard } from "@/lib/api/dashboard";
import { listLeads } from "@/lib/api/leads";
import { getQueueHealth } from "@/lib/api/jobs";
import { useAuth } from "@/lib/auth-context";
import type { AnalyticsDashboardResponse, LeadListResponse, JobQueueHealthResponse } from "@/lib/types";

function fmt(n: number): string {
  return n.toLocaleString();
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const PIPELINE_STAGES = [
  { key: "processing", label: "Extracting" },
  { key: "brief_ready", label: "Brief" },
  { key: "site_generated", label: "Generating" },
  { key: "ready_to_publish", label: "QA" },
  { key: "published", label: "Published" },
] as const;

const EMPTY_HEALTH: JobQueueHealthResponse = {
  totalJobs: 0,
  queuedJobs: 0,
  runningJobs: 0,
  failedJobs: 0,
  completedJobs: 0,
  stalledJobs: 0,
  backlogJobs: 0,
  byType: {},
  stalledItems: [],
  failedItems: [],
  queuedItems: [],
  updatedAt: new Date(0).toISOString(),
};

const EMPTY_LEADS: LeadListResponse = {
  items: [],
  pagination: { total: 0, limit: 50, offset: 0 },
  pipelineSummary: null,
};

const EMPTY_DASHBOARD: AnalyticsDashboardResponse = {
  summary: {
    totalEvents: 0,
    totalPageViews: 0,
    totalCTAClicks: 0,
    totalOutboundClicks: 0,
    totalCalendlyClicks: 0,
    totalSectionExposures: 0,
    totalFormInteractions: 0,
    uniqueSessions: 0,
    totalSites: 0,
    totalLeads: 0,
    eventsByType: {},
    topPages: [],
    topSources: [],
    referrers: [],
    messageAttribution: [],
    recentErrors: [],
    updatedAt: new Date(0).toISOString(),
  },
  siteMetrics: [],
  leadMetrics: [],
  variantMetrics: [],
  messageMetrics: [],
};

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const [dashboard, setDashboard] = useState<AnalyticsDashboardResponse>(EMPTY_DASHBOARD);
  const [leadsResponse, setLeadsResponse] = useState<LeadListResponse>(EMPTY_LEADS);
  const [health, setHealth] = useState<JobQueueHealthResponse>(EMPTY_HEALTH);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;

    setDataLoading(true);
    void Promise.all([
      getAnalyticsDashboard(),
      listLeads({ limit: 50 }),
      getQueueHealth(),
    ]).then(([d, l, h]) => {
      setDashboard(d);
      setLeadsResponse(l);
      setHealth(h);
      setDataLoading(false);
    });
  }, [authLoading, user]);

  const { summary } = dashboard;
  const pipeline = leadsResponse.pipelineSummary;
  const needsAttention = leadsResponse.items.filter(
    (l) => l.pipelineStage === "needs_attention"
  );
  const blockedSites = leadsResponse.items.filter(
    (l) => l.pipelineStage === "qa" && l.pipelineStatusDetail?.includes("blocked")
  );

  const recentLeads = [...leadsResponse.items]
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, 10);

  const hasAttentionItems =
    needsAttention.length > 0 || blockedSites.length > 0 || health.failedJobs > 0;

  if (authLoading || dataLoading) {
    return (
      <PageFrame eyebrow="Dashboard" title="Dashboard" description="What needs attention right now.">
        <div className="text-sm text-muted">Loading…</div>
      </PageFrame>
    );
  }

  return (
    <PageFrame
      eyebrow="Dashboard"
      title="Dashboard"
      description="What needs attention right now."
    >
      {/* Attention required */}
      {hasAttentionItems && (
        <section className="space-y-3">
          <h2 className="text-xs uppercase tracking-[0.18em] text-muted">Attention required</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {needsAttention.map((lead) => (
              <Link
                key={lead.id}
                href={`/app/leads/${lead.id}`}
                className="flex items-start gap-3 rounded-2xl border border-red-500/30 bg-red-500/5 p-4 transition-colors hover:bg-red-500/10"
              >
                <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-red-400" />
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-text">
                    {lead.companyName ?? lead.websiteUrl}
                  </div>
                  <div className="mt-0.5 text-xs text-muted">
                    {lead.pipelineStatusDetail ?? "Needs attention"}
                  </div>
                </div>
              </Link>
            ))}
            {health.failedJobs > 0 && (
              <Link
                href="/app/scale"
                className="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 transition-colors hover:bg-amber-500/10"
              >
                <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text">{health.failedJobs} failed job{health.failedJobs !== 1 ? "s" : ""}</div>
                  <div className="mt-0.5 text-xs text-muted">View queue health →</div>
                </div>
              </Link>
            )}
            {health.stalledJobs > 0 && (
              <Link
                href="/app/scale"
                className="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 transition-colors hover:bg-amber-500/10"
              >
                <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text">{health.stalledJobs} stalled job{health.stalledJobs !== 1 ? "s" : ""}</div>
                  <div className="mt-0.5 text-xs text-muted">Running &gt;30 min — check scale →</div>
                </div>
              </Link>
            )}
          </div>
        </section>
      )}

      {/* Pipeline summary diagram */}
      {pipeline && (
        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>Live count at each stage across all leads.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-0 overflow-x-auto">
              {PIPELINE_STAGES.map((stage, i) => {
                const count = pipeline[stage.key as keyof typeof pipeline] as number;
                return (
                  <div key={stage.key} className="flex items-center">
                    <Link
                      href={`/app/leads`}
                      className="flex min-w-[80px] flex-col items-center gap-1.5 rounded-2xl border border-line bg-panel-2 px-4 py-3 text-center transition-colors hover:bg-panel"
                    >
                      <span className="text-2xl font-semibold text-text">{fmt(count)}</span>
                      <span className="text-[10px] uppercase tracking-widest text-muted">{stage.label}</span>
                    </Link>
                    {i < PIPELINE_STAGES.length - 1 && (
                      <span className="shrink-0 px-1 text-muted">→</span>
                    )}
                  </div>
                );
              })}
              {pipeline.needs_attention > 0 && (
                <>
                  <span className="shrink-0 px-2 text-muted">·</span>
                  <Link
                    href="/app/leads"
                    className="flex min-w-[80px] flex-col items-center gap-1.5 rounded-2xl border border-red-500/30 bg-red-500/5 px-4 py-3 text-center transition-colors hover:bg-red-500/10"
                  >
                    <span className="text-2xl font-semibold text-red-400">{fmt(pipeline.needs_attention)}</span>
                    <span className="text-[10px] uppercase tracking-widest text-muted">Blocked</span>
                  </Link>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main grid: activity feed + engagement snapshot */}
      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        {/* Recent activity feed */}
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>Leads sorted by last pipeline update.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {recentLeads.length ? (
              recentLeads.map((lead) => (
                <div key={lead.id} className="flex items-center gap-3 rounded-2xl border border-line bg-panel-2 px-4 py-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-text truncate">
                        {lead.companyName ?? lead.websiteUrl}
                      </span>
                      <Badge className="shrink-0 text-[10px]">{lead.pipelineStage.replace(/_/g, " ")}</Badge>
                    </div>
                    {lead.pipelineStatusDetail && (
                      <div className="mt-0.5 text-xs text-muted truncate">{lead.pipelineStatusDetail}</div>
                    )}
                  </div>
                  <div className="shrink-0 text-xs text-muted">{relativeTime(lead.updatedAt)}</div>
                  <Link
                    href={`/app/leads/${lead.id}`}
                    className="shrink-0 text-xs text-muted underline-offset-2 hover:text-text hover:underline"
                  >
                    View →
                  </Link>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No leads yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Right column: engagement snapshot + queue mini-panel */}
        <div className="space-y-4">
          {/* Engagement snapshot */}
          <Card>
            <CardHeader>
              <CardTitle>Engagement</CardTitle>
              <CardDescription>Across all published previews.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                { label: "Visits", value: fmt(summary.totalPageViews) },
                { label: "CTA clicks", value: fmt(summary.totalCTAClicks) },
                { label: "Sessions", value: fmt(summary.uniqueSessions) },
                { label: "Booked calls", value: fmt(summary.totalCalendlyClicks) },
              ].map((stat) => (
                <div key={stat.label} className="flex items-center justify-between rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
                  <span className="text-muted">{stat.label}</span>
                  <span className="font-semibold text-text">{stat.value}</span>
                </div>
              ))}
              <Link
                href="/app/analytics"
                className="mt-1 block text-right text-xs text-muted underline-offset-2 hover:text-text hover:underline"
              >
                Full analytics →
              </Link>
            </CardContent>
          </Card>

          {/* Queue health mini-panel */}
          <Card>
            <CardHeader>
              <CardTitle>Queue health</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
                <span className="text-muted">Failed</span>
                <span className={health.failedJobs > 0 ? "font-semibold text-rose-400" : "font-semibold text-text"}>
                  {fmt(health.failedJobs)}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
                <span className="text-muted">Stalled</span>
                <span className={health.stalledJobs > 0 ? "font-semibold text-amber-400" : "font-semibold text-text"}>
                  {fmt(health.stalledJobs)}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-line bg-panel-2 px-3 py-2 text-sm">
                <span className="text-muted">Running</span>
                <span className="font-semibold text-text">{fmt(health.runningJobs)}</span>
              </div>
              <Link
                href="/app/scale"
                className="mt-1 block text-right text-xs text-muted underline-offset-2 hover:text-text hover:underline"
              >
                View all →
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent job failures */}
      {summary.recentErrors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent job failures</CardTitle>
            <CardDescription>
              Errors from the background queue.{" "}
              <Link href="/app/scale" className="underline-offset-2 hover:underline">
                View all in Scale →
              </Link>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary.recentErrors.map((error) => (
              <div key={error.id} className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-medium text-text">{error.jobType}</span>
                  <Badge className="border-white/10 bg-white/5 text-xs text-muted">
                    {relativeTime(
                      typeof error.updatedAt === "string"
                        ? error.updatedAt
                        : new Date(error.updatedAt).toISOString()
                    )}
                  </Badge>
                </div>
                <div className="mt-1.5 text-sm text-muted">{error.step}</div>
                <div className="mt-1 text-sm text-rose-200">{error.errorMessage ?? "No error message recorded."}</div>
                {error.leadId && (
                  <div className="mt-2 text-xs">
                    Lead:{" "}
                    <Link className="text-text underline-offset-2 hover:underline" href={`/app/leads/${error.leadId}`}>
                      {error.leadId.slice(0, 8)}…
                    </Link>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </PageFrame>
  );
}
