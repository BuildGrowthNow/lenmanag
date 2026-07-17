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

export interface BrandAssets {
  logoUrl?: string;
  primaryColor?: string;
  secondaryColor?: string;
  fontFamily?: string;
  imageUrls: string[];
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
