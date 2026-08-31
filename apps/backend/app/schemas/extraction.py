from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.lead import JobSummary

ExtractionStatus = Literal[
    "idle", "queued", "running", "partial", "completed", "failed"
]
SitemapStatus = Literal["unknown", "found", "missing", "blocked", "error"]
PageStatus = Literal["discovered", "crawled", "failed", "blocked"]
PageSource = Literal["homepage", "sitemap", "internal_link"]
EvidenceType = Literal[
    "title",
    "meta",
    "heading",
    "cta",
    "logo",
    "color",
    "image",
    "typography",
    "sitemap",
    "section",
    "asset",
    "visual",
]
AssetKind = Literal[
    "logo", "image", "stylesheet", "script", "font", "icon", "video", "unknown"
]
SectionType = Literal[
    "header",
    "hero",
    "services",
    "proof",
    "about",
    "process",
    "pricing",
    "gallery",
    "contact",
    "footer",
    "unknown",
]
ImageCategory = Literal[
    "hero",  # Main hero/banner images
    "product",  # Product photos
    "team",  # Team/staff photos
    "facility",  # Office/building/facility photos
    "testimonial",  # Photos accompanying testimonials
    "client_logo",  # Client/partner logos
    "gallery",  # Portfolio/gallery images
    "decorative",  # UI/decorative elements
    "unknown",
]


class ExtractedTestimonial(BaseModel):
    """A real testimonial/review extracted from the website."""

    quote: str = Field(description="The actual testimonial text")
    authorName: Optional[str] = Field(
        default=None, description="Name of the person giving testimonial"
    )
    authorTitle: Optional[str] = Field(
        default=None, description="Title/role of the author"
    )
    authorCompany: Optional[str] = Field(
        default=None, description="Company of the author"
    )
    authorPhotoUrl: Optional[str] = Field(
        default=None, description="URL to author's photo"
    )
    rating: Optional[int] = Field(
        default=None, ge=1, le=5, description="Star rating if present (1-5)"
    )
    resultMetric: Optional[str] = Field(
        default=None, description="Specific result mentioned (e.g., '50% increase')"
    )
    sourceUrl: str = Field(description="Page URL where testimonial was found")
    confidence: int = Field(default=70, ge=0, le=100)


class ExtractedClientLogo(BaseModel):
    """Client/partner logo extracted from trust sections."""

    imageUrl: str
    altText: Optional[str] = None
    companyName: Optional[str] = None
    sourceUrl: str
    confidence: int = Field(default=60, ge=0, le=100)


class ExtractedFontFile(BaseModel):
    """Font file reference with actual download URL."""

    fontFamily: str = Field(description="CSS font-family name")
    fontUrl: Optional[str] = Field(
        default=None, description="Direct URL to font file (.woff, .woff2, .ttf)"
    )
    fontWeight: Optional[str] = Field(
        default=None, description="Font weight (400, 700)"
    )
    fontStyle: Optional[str] = Field(
        default=None, description="Font style (normal, italic)"
    )
    sourceType: str = Field(
        default="css", description="Source: css, google_fonts, adobe_fonts, link_tag"
    )
    sourceUrl: str = Field(description="URL of CSS/page where font was found")
    confidence: int = Field(default=60, ge=0, le=100)


class ExtractedImage(BaseModel):
    """Categorized image with metadata."""

    url: str
    altText: Optional[str] = None
    title: Optional[str] = None
    category: ImageCategory = "unknown"
    width: Optional[int] = None
    height: Optional[int] = None
    sourceUrl: str = Field(description="Page URL where image was found")
    inSection: Optional[str] = Field(
        default=None, description="Section type where image was found"
    )
    confidence: int = Field(default=60, ge=0, le=100)


class PageCitation(BaseModel):
    pageUrl: str
    evidenceType: EvidenceType
    label: str
    excerpt: str
    confidence: int


class BrandAssetCue(BaseModel):
    assetType: Literal["logo", "color", "image", "typography"]
    label: str
    value: str
    assetUrl: Optional[str] = None
    pageUrl: Optional[str] = None
    sourceUrl: str = ""
    cachedUri: Optional[str] = None
    cachedUrl: Optional[str] = None
    cachedAt: Optional[datetime] = None
    expiresAt: Optional[datetime] = None
    bytes: Optional[int] = None
    checksum: Optional[str] = None
    confidence: int
    note: Optional[str] = None


class ExtractedAsset(BaseModel):
    kind: AssetKind
    url: str
    label: Optional[str] = None
    source: Optional[str] = None


class ExtractedSection(BaseModel):
    id: str
    index: int
    type: SectionType = "unknown"
    tagName: str
    selector: Optional[str] = None
    heading: Optional[str] = None
    text: str = ""
    html: Optional[str] = None
    ctas: list[str] = Field(default_factory=list)
    imageUrls: list[str] = Field(default_factory=list)
    assetUrls: list[str] = Field(default_factory=list)
    improvementNotes: list[str] = Field(default_factory=list)
    confidence: int = 0
    screenshotUrl: Optional[str] = None
    boundingBox: Optional[dict[str, float]] = None
    computedStyles: Optional[dict[str, str]] = None


class PageVisualCapture(BaseModel):
    desktopScreenshotUrl: Optional[str] = None
    mobileScreenshotUrl: Optional[str] = None
    capturedAt: Optional[datetime] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None


class PageInventoryItem(BaseModel):
    url: str
    source: PageSource
    status: PageStatus
    title: Optional[str] = None
    meta: dict[str, str | None] = Field(default_factory=dict)
    summary: Optional[str] = None
    cleanedText: Optional[str] = None
    depth: int
    ctaCount: int = 0
    confidence: int
    citations: list[PageCitation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    rawHtml: Optional[str] = None
    rawHtmlRef: Optional[str] = None
    rawHtmlHash: Optional[str] = None
    rawHtmlBytes: int = 0
    rawHtmlTruncated: bool = False
    fonts: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    headings: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    sections: list[ExtractedSection] = Field(default_factory=list)
    assets: list[ExtractedAsset] = Field(default_factory=list)
    visualCapture: Optional[PageVisualCapture] = None


class ValidatedTestimonial(BaseModel):
    """LLM-validated testimonial (cleaned from raw extraction)."""

    quote: str
    authorName: Optional[str] = None
    authorTitle: Optional[str] = None
    authorCompany: Optional[str] = None
    isVerified: bool = False


class ValidatedClientLogo(BaseModel):
    """LLM-validated client logo."""

    companyName: str


class ExtractionAnalysis(BaseModel):
    """LLM-analyzed semantic data from extraction."""

    services: list[str] = Field(default_factory=list)
    tone: str = "Professional"
    primaryCTAs: list[str] = Field(default_factory=list)
    audience: str = ""
    valueProposition: str = ""
    positioning: str = ""
    confidence: int = 0
    analyzedAt: Optional[datetime] = None
    # LLM-validated content (cleaned from raw extraction)
    testimonials: list[ValidatedTestimonial] = Field(default_factory=list)
    clientLogos: list[ValidatedClientLogo] = Field(default_factory=list)


class ExtractionSummary(BaseModel):
    companyName: Optional[str] = None
    canonicalWebsiteUrl: str
    detectedWebsiteUrl: Optional[str] = None
    positioningSummary: Optional[str] = None
    audienceClues: list[str] = Field(default_factory=list)
    serviceClues: list[str] = Field(default_factory=list)
    ctaClues: list[str] = Field(default_factory=list)
    toneClues: list[str] = Field(default_factory=list)


class ExtractedContactInfo(BaseModel):
    """Verified business contact values and the page from which each was read."""
    officePhone: Optional[str] = None
    emergencyPhone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    hours: Optional[str] = None
    contactUrl: Optional[str] = None
    sourceUrl: Optional[str] = None
    confidence: int = Field(default=0, ge=0, le=100)


class ExtractionSnapshot(BaseModel):
    id: str
    leadId: str
    jobId: Optional[str] = None
    version: int
    crawlStatus: ExtractionStatus
    sitemapStatus: SitemapStatus
    pagesDiscovered: int
    pagesCrawled: int
    canonicalWebsiteUrl: str
    detectedWebsiteUrl: Optional[str] = None
    summary: ExtractionSummary
    pageInventory: list[PageInventoryItem] = Field(default_factory=list)
    sourceCitations: list[PageCitation] = Field(default_factory=list)
    brandAssetCues: list[BrandAssetCue] = Field(default_factory=list)
    assetManifest: list[ExtractedAsset] = Field(default_factory=list)
    sectionInventory: list[ExtractedSection] = Field(default_factory=list)
    visualCaptureSummary: dict[str, int] = Field(default_factory=dict)
    crawlBudgetUsed: int = 0
    crawlBudgetLimit: int = 12_000_000
    crawlTimeElapsedSeconds: Optional[int] = None
    assetCacheStats: dict[str, int] = Field(default_factory=dict)
    assetRetentionDays: int = 7
    sitemapUrls: list[str] = Field(default_factory=list)
    confidenceScore: int
    gapItems: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    analysis: Optional[ExtractionAnalysis] = None
    # Enhanced extracted content (raw, pre-LLM analysis)
    extractedTestimonials: list[ExtractedTestimonial] = Field(default_factory=list)
    extractedClientLogos: list[ExtractedClientLogo] = Field(default_factory=list)
    extractedFonts: list[ExtractedFontFile] = Field(default_factory=list)
    extractedImages: list[ExtractedImage] = Field(default_factory=list)
    contactInfo: ExtractedContactInfo = Field(default_factory=ExtractedContactInfo)
    createdAt: datetime
    updatedAt: datetime


class ExtractionJobResponse(BaseModel):
    job: JobSummary
    extraction: Optional[ExtractionSnapshot] = None


class ExtractionAnalysisResponse(BaseModel):
    """Response model for the analysis endpoint."""

    analysis: ExtractionAnalysis
    extractionId: str
    extractionVersion: int


class PageInventoryResponse(BaseModel):
    leadId: str
    extractionId: Optional[str] = None
    crawlStatus: ExtractionStatus
    sitemapStatus: SitemapStatus
    detectedWebsiteUrl: Optional[str] = None
    pagesDiscovered: int
    pagesCrawled: int
    pages: list[PageInventoryItem] = Field(default_factory=list)
    gapItems: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    updatedAt: datetime
