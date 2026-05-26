export type ResourceStatus = "idle" | "loading" | "ready" | "empty" | "error" | "unauthorized";

export type SessionUser = {
  email: string;
  name: string;
  role: "operator" | "admin";
};

export type SessionResponse = {
  authenticated: boolean;
  user: SessionUser | null;
  status: "active" | "inactive";
  expiresAt: string | null;
};

export type DashboardSummary = {
  totalLeads: number;
  activeJobs: number;
  readySites: number;
  messagesReady: number;
  visits: number;
  ctaClicks: number;
  recentErrors: Array<{
    id: string;
    label: string;
    detail: string;
  }>;
};

export type LeadSourceType = "csv" | "manual" | "crm" | "future";
export type LeadStatus = "new" | "needs_review" | "archived";
export type JobStatus = "queued" | "running" | "completed" | "failed";
export type LeadJobType = "lead_import" | "lead_create" | "lead_merge" | "site_crawl" | "site_refresh" | "site_generate" | "site_republish";

export type ExtractionStatus = "idle" | "queued" | "running" | "partial" | "completed" | "failed";
export type SitemapStatus = "unknown" | "found" | "missing" | "blocked" | "error";
export type PageStatus = "discovered" | "crawled" | "failed" | "blocked";
export type PageSource = "homepage" | "sitemap" | "internal_link";
export type EvidenceType = "title" | "meta" | "heading" | "cta" | "logo" | "color" | "image" | "typography" | "sitemap";

export type PageCitation = {
  pageUrl: string;
  evidenceType: EvidenceType;
  label: string;
  excerpt: string;
  confidence: number;
};

export type BrandAssetCue = {
  assetType: "logo" | "color" | "image" | "typography";
  label: string;
  value: string;
  sourceUrl: string;
  confidence: number;
  note: string | null;
};

export type PageInventoryItem = {
  url: string;
  source: PageSource;
  status: PageStatus;
  title: string | null;
  summary: string | null;
  depth: number;
  ctaCount: number;
  confidence: number;
  citations: PageCitation[];
  errors: string[];
};

export type ExtractionSummary = {
  companyName: string | null;
  canonicalWebsiteUrl: string;
  detectedWebsiteUrl: string | null;
  positioningSummary: string | null;
  audienceClues: string[];
  serviceClues: string[];
  ctaClues: string[];
  toneClues: string[];
};

export type ExtractionSnapshot = {
  id: string;
  leadId: string;
  jobId: string | null;
  version: number;
  crawlStatus: ExtractionStatus;
  sitemapStatus: SitemapStatus;
  pagesDiscovered: number;
  pagesCrawled: number;
  canonicalWebsiteUrl: string;
  detectedWebsiteUrl: string | null;
  summary: ExtractionSummary;
  pageInventory: PageInventoryItem[];
  sourceCitations: PageCitation[];
  brandAssetCues: BrandAssetCue[];
  sitemapUrls: string[];
  confidenceScore: number;
  gapItems: string[];
  errors: string[];
  createdAt: string;
  updatedAt: string;
};

export type PageInventoryResponse = {
  leadId: string;
  extractionId: string | null;
  crawlStatus: ExtractionStatus;
  sitemapStatus: SitemapStatus;
  detectedWebsiteUrl: string | null;
  pagesDiscovered: number;
  pagesCrawled: number;
  pages: PageInventoryItem[];
  gapItems: string[];
  errors: string[];
  updatedAt: string;
};

export type BriefApprovalState = "draft" | "needs_review" | "approved";
export type BriefSourceKind = "source_backed" | "inferred";
export type BriefReferenceKind = "page" | "asset";

export type BriefSourceReference = {
  kind: BriefReferenceKind;
  sourceUrl: string;
  label: string;
  excerpt: string;
  confidence: number;
  evidenceType: EvidenceType | null;
  assetType: "logo" | "color" | "image" | "typography" | null;
};

export type BriefEvidence = {
  sourceKind: BriefSourceKind;
  inferenceLabel: string;
  confidence: number;
  references: BriefSourceReference[];
};

export type BriefTextRecommendation = {
  value: string;
  evidence: BriefEvidence;
};

export type BriefSectionRecommendation = {
  title: string;
  rationale: string;
  evidence: BriefEvidence;
};

export type BriefProofPoint = {
  label: string;
  detail: string;
  evidence: BriefEvidence;
};

export type SiteBrief = {
  id: string;
  leadId: string;
  sourceExtractionId: string;
  sourceExtractionVersion: number;
  version: number;
  approvalState: BriefApprovalState;
  needsReview: boolean;
  companySummary: BriefTextRecommendation;
  valuePropositionSummary: BriefTextRecommendation;
  audienceHypothesis: BriefTextRecommendation;
  toneProfile: BriefTextRecommendation;
  conversionAngle: BriefTextRecommendation;
  recommendedHero: BriefTextRecommendation;
  recommendedSections: BriefSectionRecommendation[];
  proofPoints: BriefProofPoint[];
  sourceCitations: BriefSourceReference[];
  brandAssetProvenance: BriefSourceReference[];
  confidenceScore: number;
  missingRequirements: string[];
  reviewNotes: string | null;
  approvedAt: string | null;
  approvedBy: string | null;
  createdAt: string;
  updatedAt: string;
};

export type PaletteMode = "zinc" | "light" | "colorful";
export type SiteReadinessStatus = "blocked" | "needs_review" | "ready_for_review" | "ready_to_publish" | "published";
export type SiteQaStatus = "pass" | "warn" | "fail";
export type OverrideScope = "copy" | "layout" | "brand" | "cta" | "motion" | "style";
export type OverrideSourceType = "manual" | "imported" | "regenerated";
export type OverrideStatus = "active" | "disabled";
export type ComparisonStatus = "matched" | "inferred" | "missing" | "mismatch";
export type RubricStatus = "pass" | "warn" | "fail";

export type SiteToken = {
  value: string;
  evidence: BriefEvidence;
};

export type BrandTokens = {
  paletteMode: PaletteMode;
  primaryColor: SiteToken;
  secondaryColor: SiteToken;
  accentColor: SiteToken;
  backgroundColor: SiteToken;
  textColor: SiteToken;
  borderColor: SiteToken;
  logoAsset: SiteToken | null;
  typography: SiteToken;
  imageStyle: SiteToken;
  visualTone: SiteToken;
  motionIntensity: SiteToken;
  layoutDensity: SiteToken;
};

export type ThemeVariant = {
  id: string;
  themeKey: string;
  name: string;
  description: string;
  heroFamily: string;
  sectionStack: string[];
  motionPreset: string;
  typographyPairing: string;
  spacingStyle: string;
  colorTreatment: string;
  bestForIndustries: string[];
  placeholderPolicy: string;
  allowedPaletteModes: PaletteMode[];
};

export type SiteSection = {
  kind: string;
  title: string;
  eyebrow: string | null;
  headline: string;
  body: string;
  items: string[];
  ctaLabel: string | null;
  evidence: BriefEvidence;
};

export type HeroVariant = {
  headline: string;
  subheadline: string;
  supportingLine: string;
  primaryCta: string;
  secondaryCta: string;
  layout: string;
  visualTreatment: string;
  evidence: BriefEvidence;
};

export type CtaAction = {
  label: string;
  href: string;
  rationale: string;
  evidence: BriefEvidence;
};

export type CtaStrategy = {
  primary: CtaAction;
  secondary: CtaAction;
  footer: CtaAction;
};

export type SiteOverrideRecord = {
  id: string;
  siteId: string;
  leadId: string;
  version: number;
  scope: OverrideScope;
  path: string;
  value: string;
  previousValue: string | null;
  reason: string | null;
  sourceType: OverrideSourceType;
  status: OverrideStatus;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
};

export type SiteExportMetadata = {
  exportType: string;
  repoUrl: string | null;
  branch: string | null;
  commitSha: string | null;
  exportPath: string | null;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
};

export type SiteQualityCheck = {
  key: string;
  label: string;
  status: RubricStatus;
  notes: string;
  evidence: BriefEvidence | null;
};

export type SiteComparisonEntry = {
  label: string;
  sourceValue: string;
  generatedValue: string;
  status: ComparisonStatus;
  reason: string;
  evidence: BriefEvidence | null;
};

export type GeneratedSiteVersion = {
  id: string;
  siteId: string;
  leadId: string;
  generationJobId: string | null;
  version: number;
  briefId: string;
  briefVersion: number;
  themeId: string;
  themeKey: string;
  themeName: string;
  themeRationale: string;
  paletteMode: PaletteMode;
  paletteRationale: string;
  brandTokens: BrandTokens;
  heroVariant: HeroVariant;
  sectionStack: SiteSection[];
  ctaStrategy: CtaStrategy;
  qualityScore: number;
  readinessStatus: SiteReadinessStatus;
  qaStatus: SiteQaStatus;
  reviewRubric: SiteQualityCheck[];
  comparisonEntries: SiteComparisonEntry[];
  sourceTraceability: BriefSourceReference[];
  missingRequirements: string[];
  previewSlug: string;
  previewUrl: string;
  overrideCount: number;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
};

export type GeneratedSite = {
  id: string;
  leadId: string;
  generationJobId: string | null;
  briefId: string;
  briefVersion: number;
  version: number;
  themeId: string;
  themeKey: string;
  themeName: string;
  themeRationale: string;
  paletteMode: PaletteMode;
  paletteRationale: string;
  brandTokens: BrandTokens;
  heroVariant: HeroVariant;
  sectionStack: SiteSection[];
  ctaStrategy: CtaStrategy;
  qualityScore: number;
  readinessStatus: SiteReadinessStatus;
  qaStatus: SiteQaStatus;
  reviewRubric: SiteQualityCheck[];
  comparisonEntries: SiteComparisonEntry[];
  sourceTraceability: BriefSourceReference[];
  missingRequirements: string[];
  previewSlug: string;
  previewUrl: string;
  overrideCount: number;
  overrides: SiteOverrideRecord[];
  exportMetadata: SiteExportMetadata | null;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
};

export type GeneratedSiteVersionResponse = {
  siteId: string;
  previewSlug: string;
  previewUrl: string;
  currentVersion: number;
  items: GeneratedSiteVersion[];
  updatedAt: string;
};

export type ThemeLibraryResponse = {
  items: ThemeVariant[];
};

export type SiteCompareResponse = {
  siteId: string;
  leadId: string;
  briefId: string;
  briefVersion: number;
  version: number;
  previewSlug: string;
  previewUrl: string;
  qualityScore: number;
  readinessStatus: SiteReadinessStatus;
  qaStatus: SiteQaStatus;
  entries: SiteComparisonEntry[];
  reviewRubric: SiteQualityCheck[];
  missingRequirements: string[];
  updatedAt: string;
};

export type SiteScreenshotMetadata = {
  id: string;
  label: string;
  url: string;
  capturedAt: string;
  width: number | null;
  height: number | null;
  contentHash: string | null;
  notes: string | null;
};

export type SiteReviewChecklistItem = {
  key: string;
  label: string;
  status: RubricStatus;
  notes: string;
  evidence: BriefEvidence | null;
};

export type SiteReviewRecord = {
  id: string;
  siteId: string;
  leadId: string;
  version: number;
  browserPreviewUrl: string | null;
  outcome: SiteQaStatus;
  reviewState: "not_reviewed" | "in_review" | "approved" | "warned" | "blocked";
  checklist: SiteReviewChecklistItem[];
  screenshots: SiteScreenshotMetadata[];
  notes: string | null;
  blockedReason: string | null;
  sourceAttribution: {
    leadId: string;
    sourceType: string | null;
    sourceRef: string | null;
    companyName: string | null;
    websiteUrl: string | null;
    normalizedDomain: string | null;
    extractionId: string | null;
    extractionVersion: number | null;
    briefId: string | null;
    briefVersion: number | null;
    themeKey: string | null;
    paletteMode: PaletteMode | null;
  };
  createdBy: string | null;
  reviewedAt: string;
  updatedAt: string;
};

export type SiteReviewQueueItem = {
  siteId: string;
  leadId: string;
  version: number;
  previewSlug: string;
  previewUrl: string;
  themeKey: string;
  paletteMode: PaletteMode;
  qualityScore: number;
  readinessStatus: SiteReadinessStatus;
  qaStatus: SiteQaStatus;
  publishApprovalState: "pending" | "approved" | "blocked";
  reviewState: "not_reviewed" | "in_review" | "approved" | "warned" | "blocked";
  missingRequirements: string[];
  reviewRubric: SiteQualityCheck[];
  screenshotCount: number;
  updatedAt: string;
};

export type SiteReviewQueueResponse = {
  items: SiteReviewQueueItem[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
  };
};

export type SiteReviewResponse = {
  review: SiteReviewRecord | null;
};

export type SiteHandoffRecord = {
  id: string;
  siteId: string;
  leadId: string;
  version: number;
  status: "ready" | "blocked";
  sourceAttribution: SiteReviewRecord["sourceAttribution"];
  previewSlug: string;
  previewUrl: string;
  themeKey: string;
  paletteMode: PaletteMode;
  qualityScore: number;
  readinessStatus: SiteReadinessStatus;
  qaStatus: SiteQaStatus;
  publishApprovalState: "pending" | "approved" | "blocked";
  reviewRecordId: string | null;
  reviewOutcome: SiteQaStatus | null;
  reviewChecklist: SiteReviewChecklistItem[];
  screenshots: SiteScreenshotMetadata[];
  sourceTraceability: BriefSourceReference[];
  missingRequirements: string[];
  exportMetadata: SiteExportMetadata | null;
  createdAt: string;
  updatedAt: string;
};

export type SiteGeneratePayload = {
  force?: boolean;
};

export type SiteReviewPayload = {
  browserPreviewUrl?: string | null;
  outcome: SiteQaStatus;
  checklist?: SiteReviewChecklistItem[];
  screenshots?: SiteScreenshotMetadata[];
  notes?: string | null;
  blockedReason?: string | null;
};

export type SiteReviewPatchPayload = Partial<SiteReviewPayload>;

export type JobRetryPayload = {
  reason?: string | null;
  maxRetryProgress?: number;
};

export type JobQueueHealthItem = {
  id: string;
  jobType: string;
  status: string;
  progress: number;
  step: string;
  errorMessage: string | null;
  leadIds: string[];
  retryCount: number;
  retryOfJobId: string | null;
  stalled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type JobQueueHealthResponse = {
  totalJobs: number;
  queuedJobs: number;
  runningJobs: number;
  failedJobs: number;
  completedJobs: number;
  stalledJobs: number;
  backlogJobs: number;
  byType: Record<string, number>;
  stalledItems: JobQueueHealthItem[];
  failedItems: JobQueueHealthItem[];
  updatedAt: string;
};

export type SiteOverrideCreatePayload = {
  scope: OverrideScope;
  path: string;
  value: string;
  previousValue?: string | null;
  reason?: string | null;
  sourceType?: OverrideSourceType;
};

export type MessageDraftStatus = "draft" | "edited" | "ready";

export type MessageDraft = {
  id: string;
  leadId: string;
  briefId: string;
  siteId: string | null;
  channel: string;
  subject: string;
  body: string;
  tone: string;
  angle: string;
  ctaPrimaryLabel: string | null;
  ctaPrimaryHref: string | null;
  ctaSecondaryLabel: string | null;
  ctaSecondaryHref: string | null;
  calendlyUrl: string | null;
  previewUrl: string | null;
  exportUrl: string | null;
  status: MessageDraftStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
};

export type MessageDraftListResponse = {
  leadId: string;
  items: MessageDraft[];
};

export type MessageCopyResponse = {
  id: string;
  channel: string;
  subject: string;
  body: string;
  ctaPrimaryLabel: string | null;
  ctaPrimaryHref: string | null;
  ctaSecondaryLabel: string | null;
  ctaSecondaryHref: string | null;
  calendlyUrl: string | null;
  previewUrl: string | null;
  exportUrl: string | null;
  status: MessageDraftStatus;
  updatedAt: string;
};

export type MessageDraftCreatePayload = {
  channel?: string;
};

export type MessageDraftPatchPayload = {
  subject?: string | null;
  body?: string | null;
  tone?: string | null;
  angle?: string | null;
  status?: MessageDraftStatus;
};

export type ExtractionJobResponse = {
  job: LeadJobSummary;
  extraction: ExtractionSnapshot;
};

export type LeadJobSummary = {
  id: string;
  jobType: LeadJobType;
  status: JobStatus;
  progress: number;
  step: string;
  errorMessage: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type LeadListItem = {
  id: string;
  sourceType: LeadSourceType;
  companyName: string | null;
  websiteUrl: string;
  normalizedDomain: string;
  status: LeadStatus;
  industry: string | null;
  notes: string | null;
  missingFields: string[];
  version: number;
  latestJob: LeadJobSummary | null;
  createdAt: string;
  updatedAt: string;
};

export type LeadDetail = {
  id: string;
  sourceType: LeadSourceType;
  sourceRef: string | null;
  sourceRefs: Array<{
    sourceType: LeadSourceType;
    sourceRef: string | null;
    importedAt: string;
  }>;
  companyName: string | null;
  websiteUrl: string;
  normalizedWebsiteUrl: string;
  normalizedDomain: string;
  detectedWebsiteUrl: string | null;
  status: LeadStatus;
  industry: string | null;
  notes: string | null;
  missingFields: string[];
  version: number;
  latestJob: LeadJobSummary | null;
  jobs: LeadJobSummary[];
  createdAt: string;
  updatedAt: string;
  archivedAt: string | null;
};

export type LeadUpsertPayload = {
  companyName?: string | null;
  websiteUrl: string;
  industry?: string | null;
  notes?: string | null;
};

export type LeadPatchPayload = {
  companyName?: string | null;
  websiteUrl?: string | null;
  industry?: string | null;
  notes?: string | null;
  status?: LeadStatus;
};

export type SiteBriefPatchPayload = {
  companySummary?: string | null;
  valuePropositionSummary?: string | null;
  audienceHypothesis?: string | null;
  toneProfile?: string | null;
  conversionAngle?: string | null;
  recommendedHero?: string | null;
  recommendedSections?: string[] | null;
  reviewNotes?: string | null;
};

export type LeadActionResponse = {
  lead: LeadDetail;
  created: boolean;
  merged: boolean;
  jobId: string | null;
  message: string;
};

export type LeadImportRowResult = {
  rowNumber: number;
  status: "created" | "merged" | "failed";
  leadId: string | null;
  companyName: string | null;
  websiteUrl: string | null;
  normalizedDomain: string | null;
  message: string;
  missingFields: string[];
};

export type LeadImportResponse = {
  job: LeadJobSummary;
  items: LeadImportRowResult[];
  totalRows: number;
  createdCount: number;
  mergedCount: number;
  failedCount: number;
  leadIds: string[];
};

export type JobResponse = {
  job: LeadJobSummary;
  leadIds: string[];
  metadata: Record<string, unknown>;
};

export type LeadListResponse = {
  items: LeadListItem[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
  };
};
