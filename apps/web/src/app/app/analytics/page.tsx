import { PageFrame } from "@/components/shell/page-frame";
import { AnalyticsDashboard } from "@/components/analytics-dashboard";
import { getAnalyticsDashboard } from "@/lib/api/dashboard";

export default async function AnalyticsPage() {
  const dashboard = await getAnalyticsDashboard();

  return (
    <PageFrame
      eyebrow="Outreach"
      title="Analytics"
      description="Preview engagement, CTA performance, and outreach attribution rolled up from live public preview sessions."
    >
      <AnalyticsDashboard dashboard={dashboard} />
    </PageFrame>
  );
}
