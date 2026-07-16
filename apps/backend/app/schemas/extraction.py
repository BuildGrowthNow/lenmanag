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
    sourceUrl: str
    cachedUri: Optional[str] = None
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


class ExtractionSummary(BaseModel):
    companyName: Optional[str] = None
    canonicalWebsiteUrl: str
    detectedWebsiteUrl: Optional[str] = None
    positioningSummary: Optional[str] = None
    audienceClues: list[str] = Field(default_factory=list)
    serviceClues: list[str] = Field(default_factory=list)
    ctaClues: list[str] = Field(default_factory=list)
    toneClues: list[str] = Field(default_factory=list)


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
    createdAt: datetime
    updatedAt: datetime


class ExtractionJobResponse(BaseModel):
    job: JobSummary
    extraction: Optional[ExtractionSnapshot] = None


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
