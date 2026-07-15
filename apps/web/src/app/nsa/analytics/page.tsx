import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageFrame } from "@/components/shell/page-frame";
import { getAnalyticsDashboard } from "@/lib/api/dashboard";

function formatNumber(value: number): string {
  return value.toLocaleString();
}

export default async function AnalyticsPage() {
  const dashboard = await getAnalyticsDashboard();
  const { summary, siteMetrics, leadMetrics, variantMetrics, messageMetrics } = dashboard;

  const cards = [
    { label: "Total events", value: summary.totalEvents },
    { label: "Visits", value: summary.totalPageViews },
    { label: "CTA clicks", value: summary.totalCTAClicks },
    { label: "Unique sessions", value: summary.uniqueSessions }
  ];

  const topPages = summary.topPages.slice(0, 5);
  const topSources = summary.topSources.slice(0, 5);
  const siteRows = siteMetrics.slice(0, 5);
  const leadRows = leadMetrics.slice(0, 5);
  const variantRows = variantMetrics.slice(0, 5);
  const messageRows = messageMetrics.slice(0, 5);

  return (
    <PageFrame
      eyebrow="Analytics"
      title="Operational analytics"
      description="Preview engagement, CTA performance, and attribution signals are rolled up directly from live public preview sessions."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl">{formatNumber(card.value)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Top pages</CardTitle>
            <CardDescription>Most visited preview URLs in the current window.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {topPages.length ? (
              topPages.map((page) => (
                <div key={page.pagePath} className="flex items-center justify-between rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm">
                  <span className="font-mono text-xs text-muted">{page.pagePath}</span>
                  <Badge>{page.count}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No page views recorded yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top sources</CardTitle>
            <CardDescription>UTM sources or referrers driving the most traffic.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {topSources.length ? (
              topSources.map((source) => (
                <div key={source.value} className="flex items-center justify-between rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm">
                  <span>{source.value}</span>
                  <Badge>{source.count}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No source attribution available yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Site engagement</CardTitle>
          <CardDescription>Preview-level traffic, CTA, and calendar interactions.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {siteRows.length ? (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-[0.2em] text-muted">
                  <th className="py-2">Site</th>
                  <th className="py-2">Visits</th>
                  <th className="py-2">CTA clicks</th>
                  <th className="py-2">Calendly</th>
                  <th className="py-2">Sections viewed</th>
                </tr>
              </thead>
              <tbody>
                {siteRows.map((row) => (
                  <tr key={row.siteId} className="border-t border-line/50">
                    <td className="py-3 font-mono text-xs text-muted">{row.siteId}</td>
                    <td className="py-3">{formatNumber(row.pageViews)}</td>
                    <td className="py-3">{formatNumber(row.ctaClicks)}</td>
                    <td className="py-3">{formatNumber(row.calendlyClicks)}</td>
                    <td className="py-3">{formatNumber(row.sectionExposures)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted">No site engagement yet.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Lead attribution</CardTitle>
            <CardDescription>Per-lead view of traffic vs. CTA follow-through.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {leadRows.length ? (
              leadRows.map((row) => (
                <div key={row.leadId} className="rounded-2xl border border-line bg-panel-2 p-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-muted">{row.leadId}</span>
                    <Badge>{formatNumber(row.visits)} visits</Badge>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted">
                    <div>CTA clicks: {formatNumber(row.ctaClicks)}</div>
                    <div>Booked calls: {formatNumber(row.bookedCalls)}</div>
                    <div>Form interactions: {formatNumber(row.formInteractions)}</div>
                    <div>Sources: {row.referrers.map((ref) => ref.referrer).join(", ") || "n/a"}</div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No lead-level analytics yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Variants & outreach</CardTitle>
            <CardDescription>Variant testing velocity plus outbound message engagement.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Active variants</div>
              {variantRows.length ? (
                <div className="mt-2 space-y-2">
                  {variantRows.map((variant) => (
                    <div key={variant.variantKey} className="rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs text-muted">{variant.variantKey}</span>
                        <Badge>{formatNumber(variant.pageViews)} visits</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted">CTA clicks: {formatNumber(variant.ctaClicks)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted">No theme variants have traffic yet.</p>
              )}
            </div>

            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Message channels</div>
              {messageRows.length ? (
                <div className="mt-2 space-y-2">
                  {messageRows.map((row, index) => (
                    <div key={`${row.channel}-${row.messageId || index}`} className="rounded-2xl border border-line bg-panel-2 px-4 py-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span>{row.channel}</span>
                        <Badge>{formatNumber(row.visits)} visits</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted">CTA clicks: {formatNumber(row.ctaClicks)} · Calendly: {formatNumber(row.calendlyClicks)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted">No outreach tracking events yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageFrame>
  );
}

