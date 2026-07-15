import { request } from "@/lib/api/client";
import type { AnalyticsEventPayload } from "@/lib/types";

export async function sendAnalyticsEvent(payload: AnalyticsEventPayload): Promise<void> {
  try {
    await request("/api/analytics/events", { method: "POST", body: payload });
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.warn("Analytics event failed", error);
    }
  }
}
