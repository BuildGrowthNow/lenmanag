import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageFrame } from "@/components/shell/page-frame";
import { getAnalyticsDashboard } from "@/lib/api/dashboard";

function formatNumber(value: number): string {
  return value.toLocaleString();
}

export default async function DashboardPage() {
  const dashboard = await getAnalyticsDashboard();
  const { summary } = dashboard;

  const cards = [
    { label: "Visits", value: summary.totalPageViews },
    { label: "CTA clicks", value: summary.totalCTAClicks },
    { label: "Outbound clicks", value: summary.totalOutboundClicks },
    { label: "Sessions", value: summary.uniqueSessions },
    { label: "Sources tracked", value: summary.topSources.length },
    { label: "Sites covered", value: summary.totalSites }
  ];

  const topPages = summary.topPages.slice(0, 4);
  const topSources = summary.topSources.slice(0, 4);

  return (
    <PageFrame
      eyebrow="Dashboard"
      title="Internal operator control center"
      description="A quick read on preview engagement, CTA follow-through, and attribution. Drill into the Analytics tab for deeper breakdowns."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl">{formatNumber(card.value)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Most visited previews</CardTitle>
            <CardDescription>Live preview URLs with the highest traffic.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {topPages.length ? (
              topPages.map((page) => (
                <div key={page.pagePath} className="flex items-center justify-between rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm">
                  <span className="font-mono text-xs text-muted">{page.pagePath}</span>
                  <Badge>{formatNumber(page.count)}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No preview traffic yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Leading sources</CardTitle>
            <CardDescription>UTM sources or referrers sending visitors.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {topSources.length ? (
              topSources.map((source) => (
                <div key={source.value} className="flex items-center justify-between rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm">
                  <span>{source.value}</span>
                  <Badge>{formatNumber(source.count)}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No attribution signals yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent job failures</CardTitle>
          <CardDescription>Surfaced directly from the background queue so operators can investigate crawl or generation blockers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {summary.recentErrors.length ? (
            summary.recentErrors.map((error: (typeof summary.recentErrors)[number]) => (
              <div key={error.id} className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-text">
                  <span className="font-medium">{error.jobType}</span>
                  <Badge className="border-white/10 bg-white/5 text-xs text-muted">
                    {new Date(error.updatedAt).toLocaleString()}
                  </Badge>
                </div>
                <div className="mt-2 text-sm text-muted">{error.step}</div>
                <div className="mt-2 text-sm text-rose-100">{error.errorMessage || "No error message recorded."}</div>
                {error.leadId ? (
                  <div className="mt-2 text-xs">
                    Related lead: <Link className="text-accent" href={`/nsa/leads/${error.leadId}`}>{error.leadId.slice(0, 8)}</Link>
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">No failed jobs in the last batch of runs.</p>
          )}
        </CardContent>
      </Card>
    </PageFrame>
  );
}

