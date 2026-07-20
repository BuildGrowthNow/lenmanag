import { safeRequest } from "@/lib/api/client";
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

export async function getAnalyticsDashboard(): Promise<AnalyticsDashboardResponse> {
  return safeRequest<AnalyticsDashboardResponse>("/api/analytics/dashboard", EMPTY_DASHBOARD);
}

