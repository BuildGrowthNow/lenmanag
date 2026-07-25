"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsDashboardResponse, AnalyticsSiteMetrics } from "@/lib/types";
import { cn } from "@/lib/utils";

function fmt(n: number) {
  return n.toLocaleString();
}

function pct(a: number, b: number) {
  if (!b) return "—";
  return `${Math.round((a / b) * 100)}%`;
}

type Props = {
  dashboard: AnalyticsDashboardResponse;
  leadNames?: Record<string, string>;
};

export function AnalyticsDashboard({ dashboard, leadNames = {} }: Props) {
  const { summary, siteMetrics, leadMetrics, variantMetrics, messageMetrics } = dashboard;
  const [selectedSite, setSelectedSite] = useState<AnalyticsSiteMetrics | null>(
    siteMetrics[0] ?? null
  );

  const topSites = [...siteMetrics].sort((a, b) => b.pageViews - a.pageViews).slice(0, 10);

  function leadLabel(leadId: string | null | undefined): string {
    if (!leadId) return "—";
    return leadNames[leadId] ?? leadId.slice(0, 12);
  }

  return (
    <div className="space-y-6">
      {/* Summary strip */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Total visits", value: fmt(summary.totalPageViews) },
          { label: "CTA clicks", value: fmt(summary.totalCTAClicks) },
          { label: "Unique sessions", value: fmt(summary.uniqueSessions) },
          { label: "Booked calls", value: fmt(summary.totalCalendlyClicks) },
        ].map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl">{card.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      {/* Two-panel: site list + site detail */}
      <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        {/* Left: top sites table */}
        <Card>
          <CardHeader>
            <CardTitle>Top sites</CardTitle>
            <CardDescription>Click a row to inspect engagement detail.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            {topSites.length ? (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-[0.18em] text-muted">
                    <th className="px-4 py-2.5">Company</th>
                    <th className="px-4 py-2.5 text-right">Visits</th>
                    <th className="px-4 py-2.5 text-right">CTA</th>
                    <th className="px-4 py-2.5 text-right">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {topSites.map((row) => (
                    <tr
                      key={row.siteId}
                      onClick={() => setSelectedSite(row)}
                      className={cn(
                        "cursor-pointer border-t border-line/50 transition-colors hover:bg-panel",
                        selectedSite?.siteId === row.siteId && "bg-panel"
                      )}
                    >
                      <td className="px-4 py-3 text-sm">
                        {leadLabel(row.leadId)}
                      </td>
                      <td className="px-4 py-3 text-right">{fmt(row.pageViews)}</td>
                      <td className="px-4 py-3 text-right">{fmt(row.ctaClicks)}</td>
                      <td className="px-4 py-3 text-right text-muted">
                        {pct(row.ctaClicks, row.pageViews)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="px-4 py-6 text-sm text-muted">No site engagement yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Right: selected site detail */}
        <Card>
          <CardHeader>
            <CardTitle>Site detail</CardTitle>
            <CardDescription>
              {selectedSite
                ? `Showing metrics for ${leadLabel(selectedSite.leadId)}`
                : "Select a site from the table to see detail."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedSite ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {[
                    { label: "Page views", value: fmt(selectedSite.pageViews) },
                    { label: "Unique sessions", value: fmt(selectedSite.uniqueSessions) },
                    { label: "CTA clicks", value: fmt(selectedSite.ctaClicks) },
                    { label: "Calendly", value: fmt(selectedSite.calendlyClicks) },
                    { label: "Outbound", value: fmt(selectedSite.outboundClicks) },
                    { label: "Sections viewed", value: fmt(selectedSite.sectionExposures) },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-xl border border-line bg-panel-2 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-widest text-muted">{stat.label}</div>
                      <div className="mt-0.5 text-lg font-semibold text-text">{stat.value}</div>
                    </div>
                  ))}
                </div>

                {selectedSite.themeKey && (
                  <div className="flex flex-wrap gap-2 text-xs text-muted">
                    <span>Theme: <span className="text-text">{selectedSite.themeKey}</span></span>
                    {selectedSite.variantKey && (
                      <span>Variant: <span className="text-text">{selectedSite.variantKey}</span></span>
                    )}
                    {selectedSite.leadId && (
                      <Link
                        href={`/app/leads/${selectedSite.leadId}`}
                        className="text-text underline-offset-2 hover:underline"
                      >
                        View lead →
                      </Link>
                    )}
                  </div>
                )}

                {/* Traffic sources */}
                {selectedSite.referrers.length > 0 && (
                  <div>
                    <div className="mb-2 text-xs uppercase tracking-[0.16em] text-muted">Traffic sources</div>
                    <div className="space-y-1.5">
                      {selectedSite.referrers.slice(0, 5).map((ref) => (
                        <div key={ref.referrer} className="flex items-center justify-between text-sm">
                          <span className="truncate text-muted">{ref.referrer}</span>
                          <Badge className="ml-2 shrink-0">{fmt(ref.count)}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Outreach attribution */}
                <div>
                  <div className="mb-1 text-xs uppercase tracking-[0.16em] text-muted">Outreach attribution</div>
                  <div className="text-sm text-text">
                    {fmt(selectedSite.messageAttributedVisits)} message-attributed visit{selectedSite.messageAttributedVisits !== 1 ? "s" : ""}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted">Click a site row to see breakdown.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Per-lead attribution — collapsed by default */}
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-2 rounded-2xl border border-line bg-panel px-5 py-3 text-sm font-medium text-text hover:bg-panel-2">
          <span className="mr-auto">Per-lead attribution</span>
          <span className="text-xs text-muted group-open:hidden">{leadMetrics.length} leads →</span>
          <span className="hidden text-xs text-muted group-open:inline">Collapse ▲</span>
        </summary>
        <div className="mt-3">
          <Card>
            <CardContent className="overflow-x-auto p-0">
              {leadMetrics.length ? (
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-xs uppercase tracking-[0.18em] text-muted">
                      <th className="px-4 py-2.5">Lead</th>
                      <th className="px-4 py-2.5 text-right">Visits</th>
                      <th className="px-4 py-2.5 text-right">CTA</th>
                      <th className="px-4 py-2.5 text-right">Forms</th>
                      <th className="px-4 py-2.5 text-right">Booked</th>
                      <th className="px-4 py-2.5">Referrer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leadMetrics.map((row) => (
                      <tr key={row.leadId} className="border-t border-line/50">
                        <td className="px-4 py-3">
                          <Link
                            href={`/app/leads/${row.leadId}`}
                            className="text-sm underline-offset-2 hover:text-text hover:underline"
                          >
                            {leadLabel(row.leadId)}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-right">{fmt(row.visits)}</td>
                        <td className="px-4 py-3 text-right">{fmt(row.ctaClicks)}</td>
                        <td className="px-4 py-3 text-right">{fmt(row.formInteractions)}</td>
                        <td className="px-4 py-3 text-right">{fmt(row.bookedCalls)}</td>
                        <td className="px-4 py-3 text-xs text-muted">
                          {row.referrers[0]?.referrer ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="px-4 py-6 text-sm text-muted">No lead-level data yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </details>

      {/* Variant metrics */}
      {variantMetrics.length > 0 && (
        <details className="group">
          <summary className="flex cursor-pointer list-none items-center gap-2 rounded-2xl border border-line bg-panel px-5 py-3 text-sm font-medium text-text hover:bg-panel-2">
            <span className="mr-auto">Theme variant performance</span>
            <span className="text-xs text-muted group-open:hidden">{variantMetrics.length} variants →</span>
            <span className="hidden text-xs text-muted group-open:inline">Collapse ▲</span>
          </summary>
          <div className="mt-3">
            <Card>
              <CardContent className="overflow-x-auto p-0">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-xs uppercase tracking-[0.18em] text-muted">
                      <th className="px-4 py-2.5">Variant</th>
                      <th className="px-4 py-2.5">Theme</th>
                      <th className="px-4 py-2.5">Lead</th>
                      <th className="px-4 py-2.5 text-right">Views</th>
                      <th className="px-4 py-2.5 text-right">CTA</th>
                      <th className="px-4 py-2.5 text-right">Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {variantMetrics.map((row) => (
                      <tr key={row.variantKey} className="border-t border-line/50">
                        <td className="px-4 py-3 font-mono text-xs text-muted">{row.variantKey}</td>
                        <td className="px-4 py-3 text-xs text-muted">{row.themeKey ?? "—"}</td>
                        <td className="px-4 py-3 text-sm">{leadLabel(row.leadId)}</td>
                        <td className="px-4 py-3 text-right">{fmt(row.pageViews)}</td>
                        <td className="px-4 py-3 text-right">{fmt(row.ctaClicks)}</td>
                        <td className="px-4 py-3 text-right text-muted">{pct(row.ctaClicks, row.pageViews)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </div>
        </details>
      )}

      {/* Message channel attribution */}
      {messageMetrics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Outreach channel attribution</CardTitle>
            <CardDescription>Which message channels are driving visits and CTA engagement.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line text-xs uppercase tracking-[0.18em] text-muted">
                  <th className="px-4 py-2.5">Channel</th>
                  <th className="px-4 py-2.5 text-right">Visits</th>
                  <th className="px-4 py-2.5 text-right">CTA clicks</th>
                  <th className="px-4 py-2.5 text-right">Calendly</th>
                </tr>
              </thead>
              <tbody>
                {messageMetrics.map((row, i) => (
                  <tr key={`${row.channel}-${row.messageId ?? i}`} className="border-t border-line/50">
                    <td className="px-4 py-3 capitalize">{row.channel}</td>
                    <td className="px-4 py-3 text-right">{fmt(row.visits)}</td>
                    <td className="px-4 py-3 text-right">{fmt(row.ctaClicks)}</td>
                    <td className="px-4 py-3 text-right">{fmt(row.calendlyClicks)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
