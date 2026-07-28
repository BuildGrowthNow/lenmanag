import { request, safeRequest, API_VERSION, VERSION_HEADER_NAME, VENDOR_MEDIA_TYPE, versionedPath } from "@/lib/api/client";
import type {
  GeneratedSite,
  GeneratedSiteVersionResponse,
  SiteCompareResponse,
  SiteExportMetadata,
  SiteExportRecord,
  SiteExportPayload,
  SiteGeneratePayload,
  SiteOverrideCreatePayload,
  SiteOverrideRecord,
  ThemeLibraryResponse,
  JobResponse,
  SiteReviewQueueResponse,
  SiteReviewPayload,
  SiteReviewPatchPayload,
  SiteReviewRecord,
  SiteReviewResponse,
  SiteHandoffRecord,
  RefinementPromptRecord
} from "@/lib/types";
import { API_BASE_URL } from "@/lib/constants";

export async function getVariantsForLead(leadId: string): Promise<GeneratedSite[]> {
  return safeRequest<GeneratedSite[]>(`/api/sites/variants/${leadId}`, []);
}

export async function getSites(params: { limit?: number; offset?: number } = {}): Promise<GeneratedSite[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const suffix = searchParams.toString();
  return safeRequest<GeneratedSite[]>(suffix ? `/api/sites?${suffix}` : "/api/sites", []);
}

export async function getSite(id: string): Promise<GeneratedSite | null> {
  return safeRequest<GeneratedSite | null>(`/api/sites/${id}`, null);
}

export async function deleteSite(id: string): Promise<void> {
  await request<{ deleted: boolean }>(`/api/sites/${id}`, { method: "DELETE" });
}

export async function getSiteReviewQueue(params: { limit?: number; offset?: number } = {}): Promise<SiteReviewQueueResponse> {
  const searchParams = new URLSearchParams();
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const suffix = searchParams.toString();
  const path = suffix ? `/api/sites/review-queue?${suffix}` : "/api/sites/review-queue";
  return request<SiteReviewQueueResponse>(path);
}

export async function getDiversityReport(limit = 100): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/sites/diversity-report?limit=${limit}`);
}

export async function getSiteReviewRecord(id: string): Promise<SiteReviewRecord | null> {
  const response = await request<SiteReviewResponse>(`/api/sites/${id}/review`);
  return response.review;
}

export async function submitSiteReview(id: string, payload: SiteReviewPayload): Promise<SiteReviewRecord> {
  return request<SiteReviewRecord>(`/api/sites/${id}/review`, { method: "POST", body: payload });
}

export async function patchSiteReview(id: string, payload: SiteReviewPatchPayload): Promise<SiteReviewRecord> {
  return request<SiteReviewRecord>(`/api/sites/${id}/review`, { method: "PATCH", body: payload });
}

export async function approveSiteReview(id: string): Promise<SiteHandoffRecord> {
  return request<SiteHandoffRecord>(`/api/sites/${id}/review/approve`, { method: "POST" });
}

export async function getSiteHandoffRecord(id: string): Promise<SiteHandoffRecord | null> {
  return safeRequest<SiteHandoffRecord | null>(`/api/sites/${id}/handoff`, null);
}

export function normalizePreviewSlug(slug: string): string {
  const trimmed = slug.trim();
  let decoded = trimmed;
  try {
    decoded = decodeURIComponent(trimmed);
  } catch {
    decoded = trimmed;
  }
  return decoded.replace(/[`'"\s]+$/g, "");
}

export async function getPublicSite(slug: string): Promise<GeneratedSite | null> {
  return safeRequest<GeneratedSite | null>(`/api/public/sites/${encodeURIComponent(normalizePreviewSlug(slug))}`, null);
}

export async function getSiteVersions(id: string): Promise<GeneratedSiteVersionResponse | null> {
  return safeRequest<GeneratedSiteVersionResponse | null>(`/api/sites/${id}/versions`, null);
}

export async function getSiteCompare(id: string): Promise<SiteCompareResponse | null> {
  return safeRequest<SiteCompareResponse | null>(`/api/sites/${id}/compare`, null);
}

export async function getThemes(): Promise<ThemeLibraryResponse> {
  return safeRequest<ThemeLibraryResponse>("/api/themes", { items: [] });
}

export async function generateSite(id: string, payload: SiteGeneratePayload = {}): Promise<JobResponse> {
  return request(`/api/sites/${id}/generate`, { method: "POST", body: payload });
}

export async function republishSite(id: string): Promise<JobResponse> {
  return request(`/api/sites/${id}/republish`, { method: "POST" });
}

export async function recaptureScreenshot(id: string): Promise<{ status: string; siteId: string; message: string }> {
  return request(`/api/sites/${id}/screenshot`, { method: "POST" });
}

export async function createSiteOverride(id: string, payload: SiteOverrideCreatePayload): Promise<SiteOverrideRecord> {
  return request(`/api/sites/${id}/overrides`, { method: "POST", body: payload });
}

export async function disableSiteOverride(id: string, overrideId: string): Promise<SiteOverrideRecord> {
  return request(`/api/sites/${id}/overrides/${overrideId}`, { method: "DELETE" });
}

export async function recordSiteExport(id: string, payload: SiteExportPayload): Promise<SiteExportMetadata> {
  return request(`/api/sites/${id}/export`, { method: "POST", body: payload });
}

export async function getSiteExportHistory(id: string): Promise<SiteExportRecord[]> {
  return request(`/api/sites/${id}/export/history`);
}

export async function downloadSiteBundle(id: string): Promise<{ blob: Blob; filename: string }> {
  const bundlePath = versionedPath(`/api/sites/${id}/export/bundle`);

  let authToken: string | null = null;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("access_token");
  }

  const response = await fetch(`${API_BASE_URL}${bundlePath}`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: `${VENDOR_MEDIA_TYPE}, application/zip`,
      [VERSION_HEADER_NAME]: API_VERSION,
      "X-Requested-With": "lenmanag-admin",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
    }
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Unable to download bundle.");
  }
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || `${id}-bundle.zip`;
  const blob = await response.blob();
  return { blob, filename };
}

export async function syncExportEdits(id: string, exportId: string, edits: Array<{ path: string; value: string; reason?: string }>): Promise<SiteOverrideRecord[]> {
  return request<SiteOverrideRecord[]>(`/api/sites/${id}/export/${exportId}/sync`, { method: "POST", body: edits });
}

export async function refineSite(
  siteId: string,
  prompt: string,
): Promise<{ siteId: string; jobId: string; status: string }> {
  const job = await request<JobResponse>(`/api/sites/${siteId}/refine`, {
    method: "POST",
    body: { refinementPrompt: prompt },
  });

  return { siteId, jobId: job.job.id, status: job.job.status };
}

export async function submitRefinementPrompt(
  siteId: string,
  prompt: string,
  force = false
): Promise<{ siteId: string; jobId: string; status: string }> {
  const job = await request<JobResponse>(`/api/sites/${siteId}/regenerate`, {
    method: "POST",
    body: { refinementPrompt: prompt, force }
  });

  return { siteId, jobId: job.job.id, status: job.job.status };
}

export async function getPromptHistory(siteId: string): Promise<RefinementPromptRecord[]> {
  return request<RefinementPromptRecord[]>(`/api/sites/${siteId}/prompts`);
}

export async function getSiteLatestJob(siteId: string): Promise<JobResponse | null> {
  return safeRequest<JobResponse | null>(`/api/sites/${siteId}/latest-job`, null);
}

/**
 * Check if lead has variants ready for client sharing.
 * Returns true if at least one successfully compiled site with screenshot exists.
 */
export async function hasVariantsReadyForSharing(leadId: string): Promise<boolean> {
  const variants = await getVariantsForLead(leadId);
  return variants.some(
    (v) =>
      v.compilationStatus === "success" &&
      v.readinessStatus !== "blocked"
  );
}

/**
 * Get the count of successfully compiled variants for a lead.
 */
export async function getReadyVariantCount(leadId: string): Promise<number> {
  const variants = await getVariantsForLead(leadId);
  return variants.filter(
    (v) =>
      v.compilationStatus === "success" &&
      v.readinessStatus !== "blocked"
  ).length;
}
