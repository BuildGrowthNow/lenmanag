"use client";

import { useEffect, useState } from "react";

import { AnalyticsDashboard } from "@/components/analytics-dashboard";
import { PageFrame } from "@/components/shell/page-frame";
import { getAnalyticsDashboard } from "@/lib/api/dashboard";
import { listLeads } from "@/lib/api/leads";
import type { AnalyticsDashboardResponse } from "@/lib/types";

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

export default function AnalyticsPage() {
  const [dashboard, setDashboard] = useState<AnalyticsDashboardResponse>(EMPTY_DASHBOARD);
  const [leadNames, setLeadNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAnalyticsDashboard(), listLeads({ limit: 200 })])
      .then(([dash, leads]) => {
        setDashboard(dash);
        const names: Record<string, string> = {};
        for (const lead of leads.items) {
          names[lead.id] = lead.companyName || lead.normalizedDomain || lead.id.slice(0, 8);
        }
        setLeadNames(names);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <PageFrame
      eyebrow="Outreach"
      title="Analytics"
      description="Preview engagement, CTA performance, and outreach attribution rolled up from live public preview sessions."
    >
      {loading ? (
        <div className="flex items-center justify-center py-24 text-sm text-muted">
          Loading analytics…
        </div>
      ) : (
        <AnalyticsDashboard dashboard={dashboard} leadNames={leadNames} />
      )}
    </PageFrame>
  );
}
