from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import EvidenceType

BriefApprovalState = Literal["draft", "needs_review", "approved"]
BriefSourceKind = Literal["source_backed", "inferred"]
BriefReferenceKind = Literal["page", "asset"]


class BriefSourceReference(BaseModel):
    kind: BriefReferenceKind
    sourceUrl: str
    label: str
    excerpt: str
    confidence: int
    evidenceType: Optional[EvidenceType] = None
    assetType: Optional[Literal["logo", "color", "image", "typography"]] = None


class BriefEvidence(BaseModel):
    sourceKind: BriefSourceKind
    inferenceLabel: str
    confidence: int
    references: list[BriefSourceReference] = Field(default_factory=list)


class BriefTextRecommendation(BaseModel):
    value: str
    evidence: BriefEvidence


class BriefSectionRecommendation(BaseModel):
    title: str
    rationale: str
    evidence: BriefEvidence


class BriefProofPoint(BaseModel):
    label: str
    detail: str
    evidence: BriefEvidence


class VisualCritique(BaseModel):
    sectionType: str
    originalStrengths: list[str] = Field(default_factory=list)
    originalWeaknesses: list[str] = Field(default_factory=list)
    redesignGoal: str
    contentToReuse: list[str] = Field(default_factory=list)
    contentToRewrite: list[str] = Field(default_factory=list)
    recommendedComponent: str
    visualDirection: str
    confidence: int

class VisualRedesignBrief(BaseModel):
    pageUrl: str
    critiques: list[VisualCritique] = Field(default_factory=list)
    artDirection: str = "minimal-luxe"

class SiteBrief(BaseModel):
    id: str
    leadId: str
    sourceExtractionId: str
    sourceExtractionVersion: int
    version: int
    approvalState: BriefApprovalState
    needsReview: bool
    companySummary: BriefTextRecommendation
    valuePropositionSummary: BriefTextRecommendation
    audienceHypothesis: BriefTextRecommendation
    toneProfile: BriefTextRecommendation
    conversionAngle: BriefTextRecommendation
    recommendedHero: BriefTextRecommendation
    recommendedSections: list[BriefSectionRecommendation] = Field(default_factory=list)
    proofPoints: list[BriefProofPoint] = Field(default_factory=list)
    visualRedesign: list[VisualRedesignBrief] = Field(default_factory=list)
    sourceCitations: list[BriefSourceReference] = Field(default_factory=list)
    brandAssetProvenance: list[BriefSourceReference] = Field(default_factory=list)
    confidenceScore: int
    missingRequirements: list[str] = Field(default_factory=list)
    reviewNotes: Optional[str] = None
    approvedAt: Optional[datetime] = None
    approvedBy: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class SiteBriefPatchRequest(BaseModel):
    companySummary: Optional[str] = None
    valuePropositionSummary: Optional[str] = None
    audienceHypothesis: Optional[str] = None
    toneProfile: Optional[str] = None
    conversionAngle: Optional[str] = None
    recommendedHero: Optional[str] = None
    recommendedSections: Optional[list[str]] = None
    reviewNotes: Optional[str] = None
