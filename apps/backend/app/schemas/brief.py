from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import EvidenceType

BriefApprovalState = Literal["draft", "needs_review", "approved"]

DesignMode = Literal[
    "editorial",  # Heavy typography, asymmetric layouts, magazine feel
    "immersive",  # Full-bleed hero, parallax, ambient motion, cinematic
    "interactive",  # Lots of hover states, scroll triggers, micro-animations
    "minimalist",  # High contrast, few elements, dramatic whitespace
    "playful",  # Organic shapes, bouncy animations, vibrant colors
    "corporate",  # Professional but not boring — structured with subtle polish
]
BriefSourceKind = Literal["source_backed", "inferred", "extraction"]
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


# Phase 2: Master Brief Schema (AI-Native)


class CreativeDirection(BaseModel):
    """Art direction block for the landing page design"""

    designConcept: str = Field(
        default="Modern and engaging",
        description="One-sentence creative concept (e.g., 'Floating glass cards emerging from a dark cosmos')",
    )
    heroTreatment: str = Field(
        default="Full-width hero with centered content",
        description="Specific hero approach (e.g., 'Split-screen with looping video left, kinetic typography right')",
    )
    signatureTechnique: str = Field(
        default="Smooth scroll animations",
        description="One memorable effect that makes this site stand out (e.g., 'Cursor-following gradient orb')",
    )
    layoutStrategy: str = Field(
        default="Clean grid layout",
        description="Grid philosophy (e.g., 'Asymmetric bento grid, no full-width sections except hero')",
    )
    scrollBehavior: str = Field(
        default="smooth-reveal",
        description="How the page responds to scroll (e.g., 'parallax-layers', 'snap-sections', 'smooth-reveal')",
    )
    microInteractions: list[str] = Field(
        default_factory=list,
        description="Specific hover/click/scroll micro-interactions (e.g., 'hover card tilt', 'button magnetic pull')",
    )
    colorMood: str = Field(
        default="Professional with brand accents",
        description="Emotional color direction (e.g., 'Dark mode with electric accents')",
    )
    typographyPersonality: str = Field(
        default="Clean sans-serif with clear hierarchy",
        description="Type treatment (e.g., 'Oversized display headings with tight tracking')",
    )
    inspirationKeywords: list[str] = Field(
        default_factory=list,
        description="Design vocabulary (e.g., 'editorial', 'brutalist', 'glassmorphism')",
    )
    avoidPatterns: list[str] = Field(
        default_factory=list,
        description="What NOT to do for this brand (e.g., 'generic stock photo grids', 'centered everything')",
    )


class BrandAssets(BaseModel):
    """Brand assets extracted from source site"""

    logoUrl: Optional[str] = None
    logoLightUrl: Optional[str] = None
    logoDarkUrl: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    fontFamily: Optional[str] = None
    fontUrl: Optional[str] = None
    fontWeight: Optional[str] = None
    fontStyle: Optional[str] = None
    fontFormat: Optional[str] = None
    logoVariants: list[str] = Field(default_factory=list)
    imageUrls: list[str] = Field(default_factory=list)
    imageInventory: list[dict[str, Any]] = Field(default_factory=list)
    palette: dict[str, str] = Field(default_factory=dict)
    derivedColors: list[str] = Field(default_factory=list)


class MasterBriefBrandAssetsPatch(BaseModel):
    logoUrl: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    fontFamily: Optional[str] = None
    fontUrl: Optional[str] = None
    fontWeight: Optional[str] = None
    fontStyle: Optional[str] = None
    fontFormat: Optional[str] = None
    logoVariants: Optional[list[str]] = None
    imageUrls: Optional[list[str]] = None
    imageInventory: Optional[list[dict[str, Any]]] = None
    palette: Optional[dict[str, str]] = None
    derivedColors: Optional[list[str]] = None


class PreflightAssetAction(BaseModel):
    sourceUrl: str
    action: Literal["approve", "reject", "role"]
    role: Optional[Literal["logo", "hero", "project", "gallery", "decorative"]] = None


class MasterBriefSection(BaseModel):
    """Section definition in master brief"""

    purpose: str = Field(
        ..., description="Section purpose: social-proof, services, process, cta, etc"
    )
    headline: str = Field(..., description="Section headline")
    contentSummary: str = Field(
        ..., description="What goes in this section (2-3 sentences)"
    )
    suggestedApproach: str = Field(
        ..., description="testimonial carousel, bento grid, timeline, etc"
    )
    contentPoints: list[str] = Field(
        default_factory=list, description="Key points/items to include"
    )


class MasterBrief(BaseModel):
    """AI-generated master brief that serves as the strategic foundation for site generation"""

    id: str
    leadId: str
    sourceExtractionId: str
    sourceExtractionVersion: int
    version: int
    approvalState: BriefApprovalState

    # Strategic Foundation
    businessGoal: str = Field(..., description="What this landing page should achieve")
    primaryAudience: str = Field(..., description="Who we're talking to")
    conversionAction: str = Field(..., description="The one thing we want them to do")
    valueProposition: str = Field(
        ..., description="Why they should care (1-2 sentences)"
    )
    toneAndVoice: str = Field(
        ..., description="How we sound (casual/professional/bold/etc)"
    )

    # Creative Direction
    visualStyle: str = Field(
        ..., description="Description of look/feel (minimal, bold, playful, etc)"
    )
    colorStrategy: str = Field(
        ..., description="How colors should be used (dark+neon, soft pastels, etc)"
    )
    motionLevel: Literal["none", "subtle", "moderate", "dramatic"] = Field(
        ..., description="Animation intensity"
    )
    heroMode: Literal["image_led", "typography_only"] = Field(
        default="typography_only",
        description="Explicit media contract for the hero; typography-only has no fake media shell.",
    )
    specialEffects: list[str] = Field(
        default_factory=list, description="3d-hero, parallax-scroll, particle-bg, etc"
    )
    creativeDirection: CreativeDirection = Field(
        default_factory=CreativeDirection,
        description="Detailed art direction for the page design",
    )
    designMode: Optional[
        Literal[
            "editorial",
            "immersive",
            "interactive",
            "minimalist",
            "playful",
            "corporate",
        ]
    ] = Field(
        default=None,
        description="Design mode that influences overall creative direction",
    )

    # Content Blueprint
    headline: str = Field(..., description="Main hero headline")
    subheadline: str = Field(..., description="Supporting line")
    sections: list[MasterBriefSection] = Field(
        default_factory=list, description="Ordered list of page sections"
    )
    ctaStrategy: str = Field(..., description="Primary + secondary CTAs approach")

    # Source Material
    extractedContent: dict[str, list[str]] = Field(
        default_factory=dict, description="Key content from extraction"
    )
    contactInfo: dict[str, str] = Field(default_factory=dict)
    brandAssets: BrandAssets = Field(
        default_factory=BrandAssets, description="Logo, colors, fonts found"
    )
    competitorInsights: str = Field(
        default="", description="What competitors do (from extraction)"
    )

    # Metadata
    confidenceScore: int = Field(
        ..., ge=0, le=100, description="Overall confidence in brief quality"
    )
    aiReasoning: str = Field(
        ..., description="Why the AI made these choices (shown to operator)"
    )
    missingRequirements: list[str] = Field(default_factory=list)
    reviewNotes: Optional[str] = None
    feedbackHistory: list[str] = Field(
        default_factory=list, description="User feedback from refinement loops"
    )

    approvedAt: Optional[datetime] = None
    approvedBy: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class MasterBriefRefinementRequest(BaseModel):
    """Request to refine master brief with user feedback"""

    feedback: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="User feedback for AI to incorporate",
    )


class MasterBriefApprovalRequest(BaseModel):
    """Request to approve master brief"""

    approvedBy: Optional[str] = None
    notes: Optional[str] = None
