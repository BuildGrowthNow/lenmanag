export type ResourceStatus = "idle" | "loading" | "ready" | "empty" | "error" | "unauthorized";

export type ExtractionHealth = {
  hasExtraction: boolean;
  crawlStatus: ExtractionStatus;
  updatedAt: string | null;
  version: number;
  ageHours: number | null;
  isStale: boolean;
  isRunning: boolean;
  isFailed: boolean;
  blockReason: string | null;
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
    leadId: string | null;
    jobType: string;
    step: string;
    errorMessage: string | null;
    updatedAt: string;
  }>;
};

export type LeadSourceType = "csv" | "manual" | "crm" | "future";
export type LeadStatus = "new" | "needs_review" | "archived";
export type JobStatus = "queued" | "running" | "completed" | "failed";
export type LeadJobType = "lead_import" | "lead_create" | "lead_merge" | "site_crawl" | "site_refresh" | "site_generate" | "site_republish" | "analysis_refresh";

export type PipelineStage =
  | "new"
  | "extracting"
  | "extracted"
  | "briefing"
  | "brief_ready"
  | "generating"
  | "qa"
  | "ready"
  | "published"
  | "needs_attention"
  | "archived";

export type PipelineMode = "auto" | "manual";

// Multi-variant generation types
export type VariantType = "html_v1" | "html_v2" | "html_v3" | "nextjs";
export type GenerationType = VariantType;

export type PipelineSummary = {
  processing: number;
  needs_attention: number;
  brief_ready: number;
  site_generated: number;
  ready_to_publish: number;
  published: number;
};

export type ExtractionStatus = "idle" | "queued" | "running" | "partial" | "completed" | "failed";
export type SitemapStatus = "unknown" | "found" | "missing" | "blocked" | "error";
export type PageStatus = "discovered" | "crawled" | "failed" | "blocked";
export type PageSource = "homepage" | "sitemap" | "internal_link";
export type EvidenceType = "title" | "meta" | "heading" | "cta" | "logo" | "color" | "image" | "typography" | "sitemap" | "section" | "asset" | "visual";
export type AssetKind = "logo" | "image" | "stylesheet" | "script" | "font" | "icon" | "video" | "unknown";
export type ExtractedSectionType = "header" | "hero" | "services" | "proof" | "about" | "process" | "pricing" | "gallery" | "contact" | "footer" | "unknown";

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

export type ExtractedAsset = {
  kind: AssetKind;
  url: string;
  label: string | null;
  source: string | null;
};

export type ExtractedSection = {
  id: string;
  index: number;
  type: ExtractedSectionType;
  tagName: string;
  selector: string | null;
  heading: string | null;
  text: string;
  html?: string | null;
  ctas: string[];
  imageUrls: string[];
  assetUrls: string[];
  improvementNotes: string[];
  confidence: number;
  screenshotUrl: string | null;
  boundingBox: Record<string, number> | null;
  computedStyles?: Record<string, string> | null;
};

export type PageVisualCapture = {
  desktopScreenshotUrl: string | null;
  mobileScreenshotUrl: string | null;
  capturedAt: string | null;
  width: number | null;
  height: number | null;
  error: string | null;
};

export type PageInventoryItem = {
  url: string;
  source: PageSource;
  status: PageStatus;
  title: string | null;
  meta?: Record<string, string>;
  summary: string | null;
  cleanedText?: string | null;
  depth: number;
  ctaCount: number;
  confidence: number;
  citations: PageCitation[];
  errors: string[];
  rawHtml?: string | null;
  rawHtmlRef?: string | null;
  rawHtmlHash?: string | null;
  rawHtmlBytes?: number;
  rawHtmlTruncated?: boolean;
  fonts?: string[];
  colors?: string[];
  headings?: string[];
  links?: string[];
  sections?: ExtractedSection[];
  assets?: ExtractedAsset[];
  visualCapture?: PageVisualCapture | null;
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

// Enhanced extraction types
export type ImageCategory =
  | "hero"
  | "product"
  | "team"
  | "facility"
  | "testimonial"
  | "client_logo"
  | "gallery"
  | "decorative"
  | "unknown";

export type ExtractedTestimonial = {
  quote: string;
  authorName: string | null;
  authorTitle: string | null;
  authorCompany: string | null;
  authorPhotoUrl: string | null;
  rating: number | null;
  resultMetric: string | null;
  sourceUrl: string;
  confidence: number;
};

export type ExtractedClientLogo = {
  imageUrl: string;
  altText: string | null;
  companyName: string | null;
  sourceUrl: string;
  confidence: number;
};

export type ExtractedFontFile = {
  fontFamily: string;
  fontUrl: string | null;
  fontWeight: string | null;
  fontStyle: string | null;
  sourceType: string;
  sourceUrl: string;
  confidence: number;
};

export type ExtractedImage = {
  url: string;
  altText: string | null;
  title: string | null;
  category: ImageCategory;
  width: number | null;
  height: number | null;
  sourceUrl: string;
  inSection: string | null;
  confidence: number;
};

export type ValidatedTestimonial = {
  quote: string;
  authorName: string | null;
  authorTitle: string | null;
  authorCompany: string | null;
  isVerified: boolean;
};

export type ValidatedClientLogo = {
  companyName: string;
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
  assetManifest?: ExtractedAsset[];
  sectionInventory?: ExtractedSection[];
  visualCaptureSummary?: Record<string, number>;
  sitemapUrls: string[];
  confidenceScore: number;
  gapItems: string[];
  errors: string[];
  crawlBudgetUsed?: number;
  crawlBudgetLimit?: number;
  crawlTimeElapsedSeconds?: number | null;
  assetCacheStats?: Record<string, number>;
  assetRetentionDays?: number;
  // Enhanced extraction data
  analysis?: ExtractionAnalysis | null;
  extractedTestimonials?: ExtractedTestimonial[];
  extractedClientLogos?: ExtractedClientLogo[];
  extractedFonts?: ExtractedFontFile[];
  extractedImages?: ExtractedImage[];
  createdAt: string;
  updatedAt: string;
};

export type ExtractionAnalysis = {
  services: string[];
  tone: string;
  primaryCTAs: string[];
  audience: string;
  valueProposition: string;
  positioning: string;
  confidence: number;
  analyzedAt: string | null;
  // LLM-validated content
  testimonials?: ValidatedTestimonial[];
  clientLogos?: ValidatedClientLogo[];
};

export type ExtractionAnalysisResponse = {
  analysis: ExtractionAnalysis;
  extractionId: string;
  extractionVersion: number;
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

export type SectionImprovement = {
  sectionTitle: string;
  currentIssues: string[];
  recommendedChanges: string[];
  priority: "high" | "medium" | "low";
};

export type ImprovementRecommendations = {
  overallApproach?: string;
  sectionImprovements?: SectionImprovement[];
  estimatedNewScore?: number;
  implementationNotes?: string;
};

export type VisualCritique = {
  sectionType: string;
  originalStrengths: string[];
  originalWeaknesses: string[];
  redesignGoal: string;
  contentToReuse: string[];
  contentToRewrite: string[];
  recommendedComponent: string;
  visualDirection: string;
  confidence: number;
};

export type VisualRedesignBrief = {
  pageUrl: string;
  critiques: VisualCritique[];
  artDirection: string;
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
  visualRedesign?: VisualRedesignBrief[];
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
  componentId?: string | null;
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

export type OverrideDiff = {
  overrideId: string;
  path: string;
  scope: OverrideScope;
  previousValue: any;
  currentValue: any;
  siteCurrentValue: any;
  diffType: "changed" | "added" | "removed";
};

export type SiteExportMetadata = {
  exportType: string;
  repoUrl: string | null;
  branch: string | null;
  commitSha: string | null;
  exportPath: string | null;
  notes: string | null;
  exportSyncStatus: "synced" | "out_of_sync" | "needs_review";
  lastSyncedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type SiteExportRecord = SiteExportMetadata & {
  id: string;
  siteId: string;
};

export type SiteExportPayload = {
  exportType: string;
  repoUrl?: string | null;
  branch?: string | null;
  commitSha?: string | null;
  exportPath?: string | null;
  notes?: string | null;
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
  diversityNotes: string[];
  diversityScore: number;
  layoutHash: string;
  refinementPromptId: string | null;
  promptHistory?: RefinementPromptRecord[];
  improvementRecommendations?: ImprovementRecommendations | null;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
};

export type SiteVariant = {
  id: string;
  leadId: string;
  variantType: VariantType;
  variantLabel: string;
  variantPosition: number;
  previewSlug: string;
  previewUrl: string;
  briefId: string;
  readinessStatus: SiteReadinessStatus;
  qaStatus: SiteQaStatus;
  staticHtml?: string;
  staticCssUrl?: string;
  staticJsUrl?: string;
  compiledBundleUrl?: string;
  createdAt: string;
  updatedAt: string;
};

export type GeneratedSite = {
  id: string;
  leadId: string;
  generationJobId: string | null;
  briefId: string;
  briefVersion: number;
  version: number;
  // Variant fields
  variantType?: VariantType;
  variantLabel?: string;
  variantPosition?: number;
  staticHtml?: string;
  staticCssUrl?: string;
  staticJsUrl?: string;
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
  } | null;
  browserReviewState: "not_reviewed" | "in_review" | "approved" | "warned" | "blocked";
  publishApprovalState: "pending" | "approved" | "blocked";
  screenshotRefs: SiteScreenshotMetadata[];
  latestReviewId: string | null;
  handoffRecordId: string | null;
  diversityNotes: string[];
  diversityScore: number;
  layoutHash: string;
  previewSlug: string;
  previewUrl: string;
  overrideCount: number;
  overrides: SiteOverrideRecord[];
  overrideDiffs: OverrideDiff[];
  exportMetadata: SiteExportMetadata | null;
  refinementPromptId: string | null;
  promptHistory?: RefinementPromptRecord[];
  isManuallyRefined?: boolean;
  improvementRecommendations?: ImprovementRecommendations | null;
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
  themeDiversity: Record<string, number>;
  paletteDiversity: Record<string, number>;
  motionDiversity: Record<string, number>;
  spacingDiversity: Record<string, number>;
  automationSummary: {
    ready: number;
    needsReview: number;
    blocked: number;
    regenerationBacklog: number;
  };
  handoffReadySiteIds: string[];
};

export type RefinementPromptStatus = "pending" | "success" | "failed";

export type RefinementPromptRecord = {
  id: string;
  submittedAt: string;
  operatorId: string;
  promptText: string;
  resultVersionId: string | null;
  status: RefinementPromptStatus;
  qualityScore: number | null;
  failureReason: string | null;
  notes: string | null;
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
  refinementPromptId?: string | null;
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

export type AnalyticsEventType =
  | "page_view"
  | "hero_cta_click"
  | "secondary_cta_click"
  | "contact_click"
  | "calendly_click"
  | "section_exposure"
  | "form_interaction"
  | "outbound_link_click"
  | "admin_action"
  | "lead_created"
  | "lead_imported"
  | "lead_merged"
  | "site_generated"
  | "site_republished"
  | "site_override_applied"
  | "site_override_disabled"
  | "site_export_created"
  | "message_draft_created"
  | "message_draft_edited"
  | "message_marked_ready"
  | "message_marked_sent"
  | "message_reset_to_draft"
  | "site_opened"
  | "brief_approved"
  | "brief_edited"
  | "theme_variant_changed"
  | "generation_regenerated";

export type AnalyticsEventPayload = {
  siteId?: string;
  leadId?: string;
  sessionId?: string;
  visitorFingerprint?: string;
  themeKey?: string;
  variantKey?: string;
  messageId?: string;
  messageChannel?: string;
  eventType: AnalyticsEventType;
  eventName: string;
  pagePath?: string;
  referrer?: string;
  utm?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type AnalyticsSummary = {
  totalEvents: number;
  totalPageViews: number;
  totalCTAClicks: number;
  totalOutboundClicks: number;
  totalCalendlyClicks: number;
  totalSectionExposures: number;
  totalFormInteractions: number;
  uniqueSessions: number;
  totalSites: number;
  totalLeads: number;
  eventsByType: Record<string, number>;
  topPages: Array<{ pagePath: string; count: number }>;
  topSources: Array<{ value: string; count: number }>;
  referrers: Array<{ referrer: string; count: number }>;
  messageAttribution: Array<{ value: string; count: number }>;
  recentErrors: Array<{
    id: string;
    leadId: string | null;
    jobType: string;
    step: string;
    errorMessage: string | null;
    updatedAt: string;
  }>;
  updatedAt: string;
};

export type AnalyticsSiteMetrics = {
  siteId: string;
  leadId: string | null;
  themeKey: string | null;
  variantKey: string | null;
  pageViews: number;
  uniqueSessions: number;
  heroCtaClicks: number;
  secondaryCtaClicks: number;
  contactClicks: number;
  ctaClicks: number;
  outboundClicks: number;
  calendlyClicks: number;
  sectionExposures: number;
  formInteractions: number;
  messageAttributedVisits: number;
  timeOnPageSeconds: number | null;
  referrers: Array<{ referrer: string; count: number }>;
  updatedAt: string;
};

export type AnalyticsLeadMetrics = {
  leadId: string;
  siteId: string | null;
  themeKey: string | null;
  visits: number;
  uniqueSessions: number;
  heroCtaClicks: number;
  secondaryCtaClicks: number;
  contactClicks: number;
  ctaClicks: number;
  bookedCalls: number;
  outboundClicks: number;
  formInteractions: number;
  messageAttributedVisits: number;
  referrers: Array<{ referrer: string; count: number }>;
  updatedAt: string;
};

export type AnalyticsVariantMetrics = {
  variantKey: string;
  themeKey: string | null;
  siteId: string | null;
  leadId: string | null;
  pageViews: number;
  uniqueSessions: number;
  ctaClicks: number;
  outboundClicks: number;
  calendlyClicks: number;
  updatedAt: string;
};

export type AnalyticsMessageMetrics = {
  channel: string;
  messageId: string | null;
  leadId: string | null;
  siteId: string | null;
  visits: number;
  ctaClicks: number;
  calendlyClicks: number;
  outboundClicks: number;
  updatedAt: string;
};

export type AnalyticsDashboardResponse = {
  summary: AnalyticsSummary;
  siteMetrics: AnalyticsSiteMetrics[];
  leadMetrics: AnalyticsLeadMetrics[];
  variantMetrics: AnalyticsVariantMetrics[];
  messageMetrics: AnalyticsMessageMetrics[];
};

export type SiteOverrideCreatePayload = {
  scope: OverrideScope;
  path: string;
  value: string;
  previousValue?: string | null;
  reason?: string | null;
  sourceType?: OverrideSourceType;
};

export type MessageDraftStatus = "draft" | "edited" | "ready" | "sent" | "failed";
export type DeliveryChannel = "whatsapp" | "linkedin" | "email" | "generic";

export type TonePreset = {
  id: string;
  name: string;
  description: string;
  example: string;
};

export type CtaVariant = {
  id: string;
  name: string;
  description: string;
  label: string;
  position: string;
};

export type PreviewContextResponse = {
  draftId: string;
  leadId: string;
  briefSummary: string | null;
  sitePreviewUrl: string | null;
  sitePreviewSlug: string | null;
  ctaPrimaryLabel: string | null;
  ctaPrimaryHref: string | null;
  ctaSecondaryLabel: string | null;
  ctaSecondaryHref: string | null;
  calendlyUrl: string | null;
  exportUrl: string | null;
};

export type MessageDraft = {
  id: string;
  leadId: string;
  briefId: string;
  siteId: string | null;
  channel: string;
  deliveryChannel: DeliveryChannel;
  subject: string;
  body: string;
  tone: string;
  tonePreset: string | null;
  customTone: string | null;
  angle: string;
  ctaVariant: string | null;
  ctaPosition: string | null;
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
  tonePreset?: string | null;
  customTone?: string | null;
  angle?: string | null;
  ctaVariant?: string | null;
  ctaPosition?: string | null;
  deliveryChannel?: DeliveryChannel;
  calendlyUrl?: string | null;
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
  pipelineStage: PipelineStage;
  pipelineMode: PipelineMode;
  pipelineStatusDetail: string | null;
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
  pipelineStage: PipelineStage;
  pipelineMode: PipelineMode;
  pipelineStatusDetail: string | null;
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
  pipelineMode?: PipelineMode;
  generationTypes?: GenerationType[];
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

export type MasterBriefSection = {
  purpose: string;
  headline: string;
  contentSummary: string;
  suggestedApproach: string;
  contentPoints: string[];
};

export type CreativeDirection = {
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
};

export type DesignMode = "editorial" | "immersive" | "interactive" | "minimalist" | "playful" | "corporate";

export type MasterBrief = {
  id: string;
  leadId: string;
  version: number;
  businessGoal: string;
  primaryAudience: string;
  conversionAction: string;
  valueProposition: string;
  toneAndVoice: string;
  visualStyle: string;
  colorStrategy: string;
  motionLevel: "none" | "subtle" | "moderate" | "dramatic";
  specialEffects: string[];
  creativeDirection?: CreativeDirection;
  designMode?: DesignMode;
  headline: string;
  subheadline: string;
  sections: MasterBriefSection[];
  ctaStrategy: string;
  aiReasoning: string;
  confidenceScore: number;
  approvalState: "pending" | "approved" | "rejected";
  approvedBy: string | null;
  approvedAt: string | null;
  reviewNotes: string | null;
  createdAt: string;
  updatedAt: string;
};

export type MasterBriefApprovalRequest = {
  approvedBy?: string;
  notes?: string;
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
  pipelineSummary: PipelineSummary | null;
};
