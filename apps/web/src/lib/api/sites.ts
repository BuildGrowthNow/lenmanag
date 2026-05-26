import { request, safeRequest } from "@/lib/api/client";
import type {
  GeneratedSite,
  GeneratedSiteVersionResponse,
  SiteCompareResponse,
  SiteGeneratePayload,
  SiteOverrideCreatePayload,
  ThemeLibraryResponse
} from "@/lib/types";

export async function getSite(id: string): Promise<GeneratedSite | null> {
  return safeRequest<GeneratedSite | null>(`/api/sites/${id}`, null);
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

export async function generateSite(id: string, payload: SiteGeneratePayload = {}): Promise<GeneratedSite> {
  return request(`/api/sites/${id}/generate`, { method: "POST", body: payload });
}

export async function republishSite(id: string): Promise<GeneratedSite> {
  return request(`/api/sites/${id}/republish`, { method: "POST" });
}

export async function createSiteOverride(id: string, payload: SiteOverrideCreatePayload): Promise<GeneratedSite> {
  await request(`/api/sites/${id}/overrides`, { method: "POST", body: payload });
  return getSite(id).then((site) => {
    if (!site) {
      throw new Error("Site not found after override save.");
    }
    return site;
  });
}

