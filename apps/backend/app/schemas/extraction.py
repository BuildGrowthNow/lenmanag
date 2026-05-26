from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.lead import JobSummary

ExtractionStatus = Literal["idle", "queued", "running", "partial", "completed", "failed"]
SitemapStatus = Literal["unknown", "found", "missing", "blocked", "error"]
PageStatus = Literal["discovered", "crawled", "failed", "blocked"]
PageSource = Literal["homepage", "sitemap", "internal_link"]
EvidenceType = Literal["title", "meta", "heading", "cta", "logo", "color", "image", "typography", "sitemap"]


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
    confidence: int
    note: Optional[str] = None


class PageInventoryItem(BaseModel):
    url: str
    source: PageSource
    status: PageStatus
    title: Optional[str] = None
    summary: Optional[str] = None
    depth: int
    ctaCount: int = 0
    confidence: int
    citations: list[PageCitation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


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
    sitemapUrls: list[str] = Field(default_factory=list)
    confidenceScore: int
    gapItems: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime


class ExtractionJobResponse(BaseModel):
    job: JobSummary
    extraction: ExtractionSnapshot


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
