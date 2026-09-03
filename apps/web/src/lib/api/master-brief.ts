/**
 * API client for master brief operations
 */

import { request, safeRequest } from "@/lib/api/client";

export interface MasterBriefSection {
  purpose: string;
  headline: string;
  contentSummary: string;
  suggestedApproach: string;
  contentPoints: string[];
}

export interface CreativeDirection {
  designConcept: string;
  heroTreatment: string;
  signatureTechnique: string;
  layoutStrategy: string;
  scrollBehavior: string;
  microInteractions: string[];
  colorMood: string;
  typographyPersonality: string;
  inspirationKeywords: string[];
  avoidPatterns: string[];
}

export type DesignMode = "editorial" | "immersive" | "interactive" | "minimalist" | "playful" | "corporate";

export interface BrandAssets {
  logoUrl?: string;
  primaryColor?: string;
  secondaryColor?: string;
  fontFamily?: string;
  fontUrl?: string;
  fontWeight?: string;
  fontStyle?: string;
  fontFormat?: string;
  logoVariants?: string[];
  imageUrls: string[];
  imageInventory?: Array<{ url: string; altText?: string; category?: string }>;
  palette?: Record<string, string>;
  derivedColors?: string[];
}

export interface MasterBrief {
  id: string;
  leadId: string;
  sourceExtractionId: string;
  sourceExtractionVersion: number;
  version: number;
  approvalState: 'draft' | 'needs_review' | 'approved';
  businessGoal: string;
  primaryAudience: string;
  conversionAction: string;
  valueProposition: string;
  toneAndVoice: string;
  visualStyle: string;
  colorStrategy: string;
  motionLevel: 'none' | 'subtle' | 'moderate' | 'dramatic';
  specialEffects: string[];
  creativeDirection?: CreativeDirection;
  designMode?: DesignMode;
  headline: string;
  subheadline: string;
  sections: MasterBriefSection[];
  ctaStrategy: string;
  extractedContent: Record<string, string[]>;
  brandAssets: BrandAssets;
  competitorInsights: string;
  confidenceScore: number;
  aiReasoning: string;
  missingRequirements: string[];
  reviewNotes?: string;
  feedbackHistory: string[];
  approvedAt?: string;
  approvedBy?: string;
  createdAt: string;
  updatedAt: string;
}

export async function getMasterBrief(leadId: string): Promise<MasterBrief | null> {
  return safeRequest<MasterBrief | null>(`/api/leads/${leadId}/master-brief`, null);
}

export async function createMasterBrief(leadId: string): Promise<MasterBrief> {
  return request<MasterBrief>(`/api/leads/${leadId}/master-brief`, { method: 'POST' });
}

export async function refineMasterBrief(
  leadId: string,
  feedback: string
): Promise<MasterBrief> {
  return request<MasterBrief>(`/api/leads/${leadId}/master-brief/refine`, {
    method: 'POST',
    body: { feedback }
  });
}

export async function approveMasterBrief(
  leadId: string,
  notes?: string,
  approvedBy?: string
): Promise<MasterBrief> {
  return request<MasterBrief>(`/api/leads/${leadId}/master-brief/approve`, {
    method: 'POST',
    body: { approvedBy, notes }
  });
}

export async function updateMasterBriefAssets(
  leadId: string,
  assets: Partial<BrandAssets>
): Promise<MasterBrief> {
  return request<MasterBrief>(`/api/leads/${leadId}/master-brief/assets`, {
    method: 'PATCH',
    body: assets,
  });
}

export type GenerationPreflight = {
  leadId: string;
  assetDownload: { enabled: boolean; backend: string; healthy: boolean };
  selectedLogo?: string;
  logoVariants: string[];
  heroCandidates: Array<{ url: string; altText?: string; category?: string }>;
  projectAssets: Array<{ url: string; altText?: string; category?: string }>;
  rejectedAssets: Array<{ value?: string; note?: string }>;
  sourceOnlyAssets: Array<{ value?: string; note?: string }>;
  proofEvidence: string[];
  missingRequirements: string[];
  intentionalFallbacks: string[];
  runtimeModes: Record<string, string>;
};

export async function getGenerationPreflight(leadId: string): Promise<GenerationPreflight> {
  return request<GenerationPreflight>(`/api/leads/${leadId}/preflight`);
}

export async function updatePreflightAsset(leadId: string, sourceUrl: string, action: 'approve' | 'reject' | 'role', role?: string): Promise<MasterBrief> {
  return request<MasterBrief>(`/api/leads/${leadId}/preflight/assets`, {
    method: 'POST',
    body: { sourceUrl, action, role },
  });
}
