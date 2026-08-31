from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.brief import BriefEvidence, BriefSourceReference

VariantType = Literal["html_v1", "html_v2", "html_v3", "nextjs"]
PaletteMode = Literal["zinc", "light", "colorful"]
SiteReadinessStatus = Literal[
    "blocked", "needs_review", "ready_for_review", "ready_to_publish", "published"
]
SiteQaStatus = Literal["pass", "warn", "fail"]
OverrideScope = Literal["copy", "layout", "brand", "cta", "motion", "style"]
OverrideSourceType = Literal["manual", "imported", "regenerated"]
OverrideStatus = Literal["active", "disabled"]
ComparisonStatus = Literal["matched", "inferred", "missing", "mismatch"]
RubricStatus = Literal["pass", "warn", "fail"]
PublishApprovalState = Literal["pending", "approved", "blocked"]
ReviewWorkflowState = Literal[
    "not_reviewed", "in_review", "approved", "warned", "blocked"
]


class SiteToken(BaseModel):
    value: str
    evidence: BriefEvidence


class BrandTokens(BaseModel):
    paletteMode: PaletteMode
    primaryColor: SiteToken
    secondaryColor: SiteToken
    accentColor: SiteToken
    backgroundColor: SiteToken
    textColor: SiteToken
    borderColor: SiteToken
    logoAsset: Optional[SiteToken] = None
    typography: SiteToken
    imageStyle: SiteToken
    visualTone: SiteToken
    motionIntensity: SiteToken
    layoutDensity: SiteToken


class ThemeVariant(BaseModel):
    id: str
    themeKey: str
    name: str
    description: str
    heroFamily: str
    sectionStack: list[str] = Field(default_factory=list)
    motionPreset: str
    typographyPairing: str
    spacingStyle: str
    colorTreatment: str
    bestForIndustries: list[str] = Field(default_factory=list)
    placeholderPolicy: str
    allowedPaletteModes: list[PaletteMode] = Field(default_factory=list)


class SiteSection(BaseModel):
    kind: str
    title: str
    eyebrow: Optional[str] = None
    headline: str
    body: str
    items: list[str] = Field(default_factory=list)
    ctaLabel: Optional[str] = None
    componentId: Optional[str] = None
    evidence: BriefEvidence


class HeroVariant(BaseModel):
    headline: str
    subheadline: str
    supportingLine: str
    primaryCta: str
    secondaryCta: str
    layout: str
    visualTreatment: str
    evidence: BriefEvidence


class CtaAction(BaseModel):
    label: str
    href: str
    rationale: str
    evidence: BriefEvidence


class CtaStrategy(BaseModel):
    primary: CtaAction
    secondary: CtaAction
    footer: CtaAction


class SiteOverrideRecord(BaseModel):
    id: str
    siteId: str
    leadId: str
    version: int
    scope: OverrideScope
    path: str
    value: str
    previousValue: Optional[str] = None
    reason: Optional[str] = None
    sourceType: OverrideSourceType = "manual"
    status: OverrideStatus = "active"
    createdBy: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class SiteSourceAttribution(BaseModel):
    leadId: str
    sourceType: Optional[str] = None
    sourceRef: Optional[str] = None
    companyName: Optional[str] = None
    websiteUrl: Optional[str] = None
    normalizedDomain: Optional[str] = None
    extractionId: Optional[str] = None
    extractionVersion: Optional[int] = None
    briefId: Optional[str] = None
    briefVersion: Optional[int] = None
    themeKey: Optional[str] = None
    paletteMode: Optional[PaletteMode] = None


class SiteScreenshotMetadata(BaseModel):
    id: str
    label: str
    url: str
    capturedAt: datetime
    width: Optional[int] = None
    height: Optional[int] = None
    contentHash: Optional[str] = None
    notes: Optional[str] = None


class SiteReviewChecklistItem(BaseModel):
    key: str
    label: str
    status: RubricStatus
    notes: str
    evidence: Optional[BriefEvidence] = None


class SiteReviewRequest(BaseModel):
    browserPreviewUrl: Optional[str] = None
    outcome: SiteQaStatus
    checklist: list[SiteReviewChecklistItem] = Field(default_factory=list)
    screenshots: list[SiteScreenshotMetadata] = Field(default_factory=list)
    notes: Optional[str] = None
    blockedReason: Optional[str] = None


class SiteReviewPatchRequest(BaseModel):
    browserPreviewUrl: Optional[str] = None
    outcome: Optional[SiteQaStatus] = None
    checklist: Optional[list[SiteReviewChecklistItem]] = None
    screenshots: Optional[list[SiteScreenshotMetadata]] = None
    notes: Optional[str] = None
    blockedReason: Optional[str] = None


class SiteReviewRecord(BaseModel):
    id: str
    siteId: str
    leadId: str
    version: int
    browserPreviewUrl: Optional[str] = None
    outcome: SiteQaStatus
    reviewState: ReviewWorkflowState
    checklist: list[SiteReviewChecklistItem] = Field(default_factory=list)
    screenshots: list[SiteScreenshotMetadata] = Field(default_factory=list)
    notes: Optional[str] = None
    blockedReason: Optional[str] = None
    sourceAttribution: SiteSourceAttribution
    createdBy: Optional[str] = None
    reviewedAt: datetime
    updatedAt: datetime


class SiteReviewQueueItem(BaseModel):
    siteId: str
    leadId: str
    version: int
    previewSlug: str
    previewUrl: str
    themeKey: str
    variantType: Optional[str] = None
    paletteMode: PaletteMode
    qualityScore: int
    readinessStatus: SiteReadinessStatus
    qaStatus: SiteQaStatus
    publishApprovalState: PublishApprovalState
    reviewState: ReviewWorkflowState
    missingRequirements: list[str] = Field(default_factory=list)
    reviewRubric: list[SiteQualityCheck] = Field(default_factory=list)
    screenshotCount: int = 0
    screenshotRefs: list[SiteScreenshotMetadata] = Field(default_factory=list)
    sourceAttribution: Optional[SiteSourceAttribution] = None
    isManuallyRefined: bool = False
    refinedCount: int = 0
    updatedAt: datetime


class SiteReviewQueueResponse(BaseModel):
    items: list[SiteReviewQueueItem] = Field(default_factory=list)
    pagination: dict[str, int]
    themeDiversity: dict[str, int] = Field(default_factory=dict)
    paletteDiversity: dict[str, int] = Field(default_factory=dict)
    motionDiversity: dict[str, int] = Field(default_factory=dict)
    spacingDiversity: dict[str, int] = Field(default_factory=dict)
    automationSummary: dict[str, int] = Field(default_factory=dict)
    handoffReadySiteIds: list[str] = Field(default_factory=list)


class SiteHandoffRecord(BaseModel):
    id: str
    siteId: str
    leadId: str
    version: int
    status: Literal["ready", "blocked"]
    sourceAttribution: SiteSourceAttribution
    previewSlug: str
    previewUrl: str
    themeKey: str
    paletteMode: PaletteMode
    qualityScore: int
    readinessStatus: SiteReadinessStatus
    qaStatus: SiteQaStatus
    publishApprovalState: PublishApprovalState
    reviewRecordId: Optional[str] = None
    reviewOutcome: Optional[SiteQaStatus] = None
    reviewChecklist: list[SiteReviewChecklistItem] = Field(default_factory=list)
    screenshots: list[SiteScreenshotMetadata] = Field(default_factory=list)
    sourceTraceability: list[BriefSourceReference] = Field(default_factory=list)
    missingRequirements: list[str] = Field(default_factory=list)
    exportMetadata: Optional[SiteExportMetadata] = None
    createdAt: datetime
    updatedAt: datetime


class SiteExportMetadata(BaseModel):
    exportType: str
    repoUrl: Optional[str] = None
    branch: Optional[str] = None
    commitSha: Optional[str] = None
    exportPath: Optional[str] = None
    notes: Optional[str] = None
    exportSyncStatus: Literal["synced", "out_of_sync", "needs_review"] = "synced"
    lastSyncedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime


class SiteExportRecord(SiteExportMetadata):
    id: str
    siteId: str


class SiteQualityCheck(BaseModel):
    key: str
    label: str
    status: RubricStatus
    notes: str
    evidence: Optional[BriefEvidence] = None


class SiteComparisonEntry(BaseModel):
    label: str
    sourceValue: str
    generatedValue: str
    status: ComparisonStatus
    reason: str
    evidence: Optional[BriefEvidence] = None


class RefinementPromptRecord(BaseModel):
    id: str
    submittedAt: datetime
    operatorId: str
    promptText: str
    resultVersionId: Optional[str] = None
    status: str
    qualityScore: Optional[int] = None
    failureReason: Optional[str] = None
    notes: Optional[str] = None


class GeneratedSiteVersion(BaseModel):
    id: str
    siteId: str
    leadId: str
    generationJobId: Optional[str] = None
    generationRunId: Optional[str] = None
    extractionId: Optional[str] = None
    extractionVersion: Optional[int] = None
    analysisId: Optional[str] = None
    brandRevision: Optional[int] = None
    brandSnapshotHash: Optional[str] = None
    generationInputHash: Optional[str] = None
    variantBriefId: Optional[str] = None
    variantBriefVersion: Optional[int] = None
    generatorVersion: Optional[str] = None
    promptVersion: Optional[str] = None
    version: int
    briefId: str
    briefVersion: int
    themeId: str
    themeKey: str
    themeName: str
    themeRationale: str
    paletteMode: PaletteMode
    paletteRationale: str
    brandTokens: BrandTokens
    heroVariant: HeroVariant
    sectionStack: list[SiteSection] = Field(default_factory=list)
    ctaStrategy: CtaStrategy
    navigationConfig: Optional[dict[str, Any]] = None
    qualityScore: int
    qualityScoreSource: Literal["visual", "fallback"] = "fallback"
    readinessStatus: SiteReadinessStatus
    qaStatus: SiteQaStatus
    reviewRubric: list[SiteQualityCheck] = Field(default_factory=list)
    comparisonEntries: list[SiteComparisonEntry] = Field(default_factory=list)
    sourceTraceability: list[BriefSourceReference] = Field(default_factory=list)
    missingRequirements: list[str] = Field(default_factory=list)
    sourceAttribution: Optional[SiteSourceAttribution] = None
    browserReviewState: ReviewWorkflowState = "not_reviewed"
    publishApprovalState: PublishApprovalState = "pending"
    screenshotRefs: list[SiteScreenshotMetadata] = Field(default_factory=list)
    latestReviewId: Optional[str] = None
    handoffRecordId: Optional[str] = None
    diversityNotes: list[str] = Field(default_factory=list)
    diversityScore: int = Field(
        default=50, description="0-100 score based on theme/palette uniqueness in batch"
    )
    layoutHash: str = Field(
        default="", description="Hash of layout for duplicate detection"
    )
    previewSlug: str
    previewUrl: str
    overrideCount: int
    refinementPromptId: Optional[str] = None
    promptHistory: list[RefinementPromptRecord] = Field(default_factory=list)
    isManuallyRefined: bool = False
    improvementRecommendations: dict[str, Any] | None = None
    sourceCode: Optional[str] = Field(
        default=None, description="AI-generated TSX source code for compilation"
    )
    compiledBundleUrl: Optional[str] = Field(
        default=None, description="URL to the compiled JavaScript bundle"
    )
    compilationStatus: Optional[str] = Field(
        default=None, description="Status of compilation: pending, success, failed"
    )
    compilationError: Optional[str] = Field(
        default=None, description="Error message if compilation failed"
    )
    createdAt: datetime
    updatedAt: datetime
    publishedAt: Optional[datetime] = None


class GeneratedSite(BaseModel):
    id: str
    leadId: str
    userId: str = ""
    generationJobId: Optional[str] = None
    generationRunId: Optional[str] = None
    extractionId: Optional[str] = None
    extractionVersion: Optional[int] = None
    analysisId: Optional[str] = None
    brandRevision: Optional[int] = None
    brandSnapshotHash: Optional[str] = None
    generationInputHash: Optional[str] = None
    variantBriefId: Optional[str] = None
    variantBriefVersion: Optional[int] = None
    generatorVersion: Optional[str] = None
    promptVersion: Optional[str] = None
    briefId: str
    briefVersion: int
    version: int

    # NEW: Variant identification
    variantType: VariantType = "nextjs"
    variantLabel: str = "Next.js Site"
    variantPosition: int = 1  # Display order: 1=first, 2=second, etc.

    # NEW: Static HTML output (for HTML variants only)
    staticHtml: Optional[str] = Field(
        default=None, description="Full HTML content for static variants"
    )
    staticCssUrl: Optional[str] = Field(
        default=None, description="S3 URL to styles.css for static variants"
    )
    staticJsUrl: Optional[str] = Field(
        default=None, description="S3 URL to script.js for static variants"
    )

    themeId: str
    themeKey: str
    themeName: str
    themeRationale: str
    paletteMode: PaletteMode
    paletteRationale: str
    brandTokens: BrandTokens
    heroVariant: HeroVariant
    sectionStack: list[SiteSection] = Field(default_factory=list)
    ctaStrategy: CtaStrategy
    navigationConfig: Optional[dict[str, Any]] = None
    awwwardsPatternMetadata: Optional[dict[str, Any]] = None
    qualityScore: int
    qualityScoreSource: Literal["visual", "fallback"] = "fallback"
    readinessStatus: SiteReadinessStatus
    qaStatus: SiteQaStatus
    reviewRubric: list[SiteQualityCheck] = Field(default_factory=list)
    comparisonEntries: list[SiteComparisonEntry] = Field(default_factory=list)
    sourceTraceability: list[BriefSourceReference] = Field(default_factory=list)
    missingRequirements: list[str] = Field(default_factory=list)
    sourceAttribution: Optional[SiteSourceAttribution] = None
    browserReviewState: ReviewWorkflowState = "not_reviewed"
    publishApprovalState: PublishApprovalState = "pending"
    screenshotRefs: list[SiteScreenshotMetadata] = Field(default_factory=list)
    latestReviewId: Optional[str] = None
    handoffRecordId: Optional[str] = None
    diversityNotes: list[str] = Field(default_factory=list)
    diversityScore: int = Field(
        default=50, description="0-100 score based on theme/palette uniqueness in batch"
    )
    layoutHash: str = Field(
        default="", description="Hash of layout for duplicate detection"
    )
    previewSlug: str
    previewUrl: str
    overrideCount: int
    overrides: list[SiteOverrideRecord] = Field(default_factory=list)
    overrideDiffs: list[dict[str, Any]] = Field(default_factory=list)
    exportMetadata: Optional[SiteExportMetadata] = None
    refinementPromptId: Optional[str] = None
    promptHistory: list[RefinementPromptRecord] = Field(default_factory=list)
    isManuallyRefined: bool = False
    improvementRecommendations: dict[str, Any] | None = None
    sourceCode: Optional[str] = Field(
        default=None,
        description="AI-generated TSX source code for compilation (Next.js) or HTML template (static)",
    )
    compiledBundleUrl: Optional[str] = Field(
        default=None, description="URL to the compiled JavaScript bundle (Next.js only)"
    )
    compiledCssUrl: Optional[str] = Field(default=None, description="URL to the generated per-site stylesheet")
    compilationStatus: Optional[str] = Field(
        default=None, description="Status of compilation: pending, success, failed"
    )
    compilationError: Optional[str] = Field(
        default=None, description="Error message if compilation failed"
    )
    createdAt: datetime
    updatedAt: datetime
    publishedAt: Optional[datetime] = None


class GeneratedSiteVersionResponse(BaseModel):
    siteId: str
    previewSlug: str
    previewUrl: str
    currentVersion: int
    items: list[GeneratedSiteVersion] = Field(default_factory=list)
    updatedAt: datetime


class ThemeLibraryResponse(BaseModel):
    items: list[ThemeVariant] = Field(default_factory=list)


class SiteCompareResponse(BaseModel):
    siteId: str
    leadId: str
    briefId: str
    briefVersion: int
    version: int
    previewSlug: str
    previewUrl: str
    qualityScore: int
    readinessStatus: SiteReadinessStatus
    qaStatus: SiteQaStatus
    entries: list[SiteComparisonEntry] = Field(default_factory=list)
    reviewRubric: list[SiteQualityCheck] = Field(default_factory=list)
    missingRequirements: list[str] = Field(default_factory=list)
    updatedAt: datetime


class SiteHandoffResponse(BaseModel):
    record: SiteHandoffRecord


class SiteReviewResponse(BaseModel):
    review: Optional[SiteReviewRecord] = None


class SiteExportRequest(BaseModel):
    exportType: str = "local_bundle"
    repoUrl: Optional[str] = None
    branch: Optional[str] = None
    commitSha: Optional[str] = None
    exportPath: Optional[str] = None
    notes: Optional[str] = None


class SiteGenerateRequest(BaseModel):
    force: bool = False
    refinementPromptId: Optional[str] = None
    variantTypes: Optional[list[VariantType]] = None


class SiteOverrideCreateRequest(BaseModel):
    scope: OverrideScope
    path: str
    value: str
    previousValue: Optional[str] = None
    reason: Optional[str] = None
    sourceType: OverrideSourceType = "manual"


class RedesignVariant(BaseModel):
    siteId: str
    previewUrl: str
    screenshotUrl: str = ""
    variantPosition: int
    optionNumber: int = 1
    variantLabel: Optional[str] = None


class ClientShareRequest(BaseModel):
    siteIds: list[str] = Field(..., min_length=1, max_length=4)


class ClientShareResponse(BaseModel):
    id: str
    leadId: str
    slug: str
    siteIds: list[str]
    url: str
    updatedAt: datetime


class RedesignPageData(BaseModel):
    leadId: str
    companyName: Optional[str] = None
    contactName: Optional[str] = None
    logoUrl: Optional[str] = None
    variants: list[RedesignVariant] = Field(default_factory=list)
