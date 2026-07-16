/**
 * API client for master brief operations
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface MasterBriefSection {
  purpose: string;
  headline: string;
  contentSummary: string;
  suggestedApproach: string;
  contentPoints: string[];
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
  const res = await fetch(`${API_BASE}/api/v1/leads/${leadId}/master-brief`, {
    credentials: 'include',
  });

  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch master brief: ${res.status}`);
  }

  const data = await res.json();
  return data.data;
}

export async function createMasterBrief(leadId: string): Promise<MasterBrief> {
  const res = await fetch(`${API_BASE}/api/v1/leads/${leadId}/master-brief`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Failed to create master brief: ${res.status}`);
  }

  const data = await res.json();
  return data.data;
}

export async function refineMasterBrief(
  leadId: string,
  feedback: string
): Promise<MasterBrief> {
  const res = await fetch(`${API_BASE}/api/v1/leads/${leadId}/master-brief/refine`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Failed to refine master brief: ${res.status}`);
  }

  const data = await res.json();
  return data.data;
}

export async function approveMasterBrief(
  leadId: string,
  notes?: string
): Promise<MasterBrief> {
  const res = await fetch(`${API_BASE}/api/v1/leads/${leadId}/master-brief/approve`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Failed to approve master brief: ${res.status}`);
  }

  const data = await res.json();
  return data.data;
}
