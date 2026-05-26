import { safeRequest } from "@/lib/api/client";
import type { DashboardSummary } from "@/lib/types";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return safeRequest<DashboardSummary>("/api/analytics/dashboard", {
    totalLeads: 0,
    activeJobs: 0,
    readySites: 0,
    messagesReady: 0,
    visits: 0,
    ctaClicks: 0,
    recentErrors: []
  });
}

