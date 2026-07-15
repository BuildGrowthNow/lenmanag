import { request } from "@/lib/api/client";
import type { AnalyticsDashboardResponse } from "@/lib/types";

export async function getAnalyticsDashboard(): Promise<AnalyticsDashboardResponse> {
  return request<AnalyticsDashboardResponse>("/api/analytics/dashboard");
}

