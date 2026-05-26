import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/state/empty-state";
import { PageFrame, PlaceholderPanel } from "@/components/shell/page-frame";
import { getDashboardSummary } from "@/lib/api/dashboard";

export default async function DashboardPage() {
  const summary = await getDashboardSummary();

  const cards = [
    { label: "Leads", value: summary.totalLeads },
    { label: "Jobs", value: summary.activeJobs },
    { label: "Ready sites", value: summary.readySites },
    { label: "Messages ready", value: summary.messagesReady },
    { label: "Visits", value: summary.visits },
    { label: "CTA clicks", value: summary.ctaClicks }
  ];

  return (
    <PageFrame
      eyebrow="Dashboard"
      title="Internal operator control center"
      description="Phase 1 establishes the secure shell, navigation, and API contract surface. The creation, crawl, generation, and export workflows arrive in later phases."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl">{card.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Recent issues</CardTitle>
            <CardDescription>Empty for now because later phases will feed the live job queue and analytics stream.</CardDescription>
          </CardHeader>
          <CardContent>
            {summary.recentErrors.length ? (
              <div className="space-y-3">
                {summary.recentErrors.map((error) => (
                  <div key={error.id} className="rounded-2xl border border-line bg-panel-2 px-4 py-3">
                    <div className="font-medium">{error.label}</div>
                    <div className="text-sm text-muted">{error.detail}</div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No operational errors yet"
                description="The admin shell is live, but there are no imported leads or background jobs yet."
              />
            )}
          </CardContent>
        </Card>

        <PlaceholderPanel
          title="Phase 1 shell only"
          description="This panel exists to keep the dashboard layout stable while later phases wire in lead intake, generation, analytics, and exports."
        />
      </div>
    </PageFrame>
  );
}

