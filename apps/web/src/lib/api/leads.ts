import { request, safeRequest } from "@/lib/api/client";
import type {
  ExtractionJobResponse,
  ExtractionSnapshot,
  SiteBrief,
  SiteBriefPatchPayload,
  LeadActionResponse,
  LeadDetail,
  LeadImportResponse,
  LeadListResponse,
  LeadPatchPayload,
  PageInventoryResponse,
  LeadUpsertPayload
} from "@/lib/types";

type LeadListQuery = {
  q?: string;
  status?: string;
  limit?: number;
  offset?: number;
};

function buildQuery(query: LeadListQuery = {}) {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.status) params.set("status", query.status);
  if (typeof query.limit === "number") params.set("limit", String(query.limit));
  if (typeof query.offset === "number") params.set("offset", String(query.offset));
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
}

export async function listLeads(query: LeadListQuery = {}): Promise<LeadListResponse> {
  return safeRequest(`/api/leads${buildQuery(query)}`, {
    items: [],
    pagination: { total: 0, limit: query.limit ?? 25, offset: query.offset ?? 0 },
    pipelineSummary: null,
  });
}

/**
 * Poll for lead updates at a regular interval.
 * Useful for detecting extraction job completions.
 *
 * @param query - Query parameters for lead list
 * @param callback - Called with updated results on each poll
 * @param intervalMs - Polling interval in milliseconds (default: 5000)
 * @returns cleanup function to stop polling
 */
export function pollLeadUpdates(
  query: LeadListQuery = {},
  callback: (results: LeadListResponse) => void,
  intervalMs: number = 5000
): () => void {
  let active = true;
  let timeoutId: NodeJS.Timeout | null = null;

  const poll = async () => {
    if (!active) return;

    try {
      const results = await listLeads(query);
      if (active) {
        callback(results);
      }
    } catch (error) {
      console.error("Poll error:", error);
    }

    if (active) {
      timeoutId = setTimeout(poll, intervalMs);
    }
  };

  // Start polling
  poll();

  // Return cleanup function
  return () => {
    active = false;
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  };
}

export async function getLead(id: string): Promise<LeadDetail | null> {
  return safeRequest<LeadDetail | null>(`/api/leads/${id}`, null);
}

export async function createLead(payload: LeadUpsertPayload): Promise<LeadActionResponse> {
  return request("/api/leads", { method: "POST", body: payload });
}

export async function updateLead(id: string, payload: LeadPatchPayload): Promise<LeadDetail> {
  return request(`/api/leads/${id}`, { method: "PATCH", body: payload });
}

export async function archiveLead(id: string): Promise<LeadDetail> {
  return request(`/api/leads/${id}`, { method: "DELETE" });
}

export async function importLeads(file: File): Promise<LeadImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/leads/import", { method: "POST", body: formData });
}

export async function startLeadExtraction(id: string): Promise<ExtractionJobResponse> {
  return request(`/api/leads/${id}/extraction/start`, { method: "POST" });
}

export async function refreshLeadExtraction(id: string): Promise<ExtractionJobResponse> {
  return request(`/api/leads/${id}/extraction/refresh`, { method: "POST" });
}

export async function getLeadExtraction(id: string): Promise<ExtractionSnapshot | null> {
  return safeRequest<ExtractionSnapshot | null>(`/api/leads/${id}/extraction`, null);
}

export async function getLeadPages(id: string): Promise<PageInventoryResponse | null> {
  return safeRequest<PageInventoryResponse | null>(`/api/leads/${id}/pages`, null);
}

export async function getLeadBrief(id: string): Promise<SiteBrief | null> {
  return safeRequest<SiteBrief | null>(`/api/leads/${id}/brief`, null);
}

export async function createLeadBrief(id: string): Promise<SiteBrief> {
  return request(`/api/leads/${id}/brief`, { method: "POST" });
}

export async function updateLeadBrief(id: string, payload: SiteBriefPatchPayload): Promise<SiteBrief> {
  return request(`/api/leads/${id}/brief`, { method: "PATCH", body: payload });
}

export async function approveLeadBrief(id: string): Promise<SiteBrief> {
  return request(`/api/leads/${id}/brief/approve`, { method: "POST" });
}
