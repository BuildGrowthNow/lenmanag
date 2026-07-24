from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


GenerationType = Literal["html_v1", "html_v2", "html_v3", "nextjs"]
LeadSourceType = Literal["csv", "manual", "crm", "future"]
LeadStatus = Literal["new", "needs_review", "archived"]
JobStatus = Literal["queued", "running", "completed", "failed"]
JobType = Literal[
    "lead_import",
    "lead_create",
    "lead_merge",
    "site_crawl",
    "site_refresh",
    "site_generate",
    "site_republish",
    "analysis_refresh",
]

# Pipeline event types for activity tracking
PipelineEventType = Literal[
    "lead_created",
    "lead_merged",
    "extraction_started",
    "extraction_progress",
    "extraction_completed",
    "extraction_failed",
    "analysis_started",
    "analysis_completed",
    "analysis_failed",
    "brief_generation_started",
    "brief_generated",
    "brief_approved",
    "brief_rejected",
    "site_generation_started",
    "site_generation_progress",
    "site_variant_generated",
    "site_generation_completed",
    "site_generation_failed",
    "qa_started",
    "qa_passed",
    "qa_failed",
    "site_published",
    "pipeline_error",
    "pipeline_paused",
    "pipeline_resumed",
]

PipelineEventStatus = Literal["success", "error", "info", "warning"]

# Pipeline stage reflects where a lead sits in the automation flow
PipelineStage = Literal[
    "new",
    "extracting",
    "extracted",
    "briefing",
    "brief_ready",
    "generating",
    "qa",
    "ready",
    "published",
    "needs_attention",
    "archived",
]

PipelineMode = Literal["auto", "manual"]


class PipelineEvent(BaseModel):
    """A single event in the pipeline activity log."""

    id: str
    eventType: PipelineEventType
    status: PipelineEventStatus
    message: str
    detail: Optional[str] = None
    jobId: Optional[str] = None
    variantType: Optional[str] = None
    durationMs: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class SourceReference(BaseModel):
    sourceType: LeadSourceType
    sourceRef: Optional[str] = None
    importedAt: datetime


class JobSummary(BaseModel):
    id: str
    jobType: JobType
    status: JobStatus
    progress: int
    step: str
    errorMessage: Optional[str] = None
    retryCount: int = 0
    retryOfJobId: Optional[str] = None
    startedAt: Optional[datetime] = None
    finishedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime


class JobRetryRequest(BaseModel):
    reason: Optional[str] = None
    maxRetryProgress: int = 95


class LeadBatchRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)
    limit: int = 25
    offset: int = 0


class SourceAttribution(BaseModel):
    leadId: str
    sourceType: LeadSourceType
    sourceRef: Optional[str] = None
    companyName: Optional[str] = None
    websiteUrl: Optional[str] = None
    normalizedDomain: Optional[str] = None
    extractionId: Optional[str] = None
    extractionVersion: Optional[int] = None
    briefId: Optional[str] = None
    briefVersion: Optional[int] = None
    siteId: Optional[str] = None
    siteVersion: Optional[int] = None
    exportId: Optional[str] = None
    campaignId: Optional[str] = None
    campaignLabel: Optional[str] = None


class LeadListItem(BaseModel):
    id: str
    user_id: str
    sourceType: LeadSourceType
    companyName: Optional[str] = None
    websiteUrl: str
    normalizedDomain: str
    status: LeadStatus
    pipelineStage: PipelineStage = "new"
    pipelineMode: PipelineMode = "auto"
    pipelineStatusDetail: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    missingFields: list[str] = Field(default_factory=list)
    version: int
    latestJob: Optional[JobSummary] = None
    createdAt: datetime
    updatedAt: datetime


class LeadDetail(BaseModel):
    id: str
    user_id: str
    sourceType: LeadSourceType
    sourceRef: Optional[str] = None
    sourceRefs: list[SourceReference] = Field(default_factory=list)
    companyName: Optional[str] = None
    websiteUrl: str
    normalizedWebsiteUrl: str
    normalizedDomain: str
    detectedWebsiteUrl: Optional[str] = None
    status: LeadStatus
    pipelineStage: PipelineStage = "new"
    pipelineMode: PipelineMode = "auto"
    pipelineStatusDetail: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    generationTypes: list[GenerationType] = Field(default=["nextjs"])
    missingFields: list[str] = Field(default_factory=list)
    version: int
    latestJob: Optional[JobSummary] = None
    jobs: list[JobSummary] = Field(default_factory=list)
    pipelineEvents: list[PipelineEvent] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime
    archivedAt: Optional[datetime] = None


class LeadUpsertRequest(BaseModel):
    companyName: Optional[str] = None
    websiteUrl: str
    industry: Optional[str] = None
    notes: Optional[str] = None
    pipelineMode: PipelineMode = "auto"

    generationTypes: list[GenerationType] = Field(
        default=["nextjs"],
        description="Types of sites to generate. Can select 1-4 options.",
        min_length=1,
        max_length=4,
    )


class LeadPatchRequest(BaseModel):
    companyName: Optional[str] = None
    websiteUrl: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[LeadStatus] = None
    pipelineMode: Optional[PipelineMode] = None
    pipelineStage: Optional[PipelineStage] = None
    generationTypes: Optional[list[GenerationType]] = None


class ImportRowResult(BaseModel):
    rowNumber: int
    status: Literal["created", "merged", "failed"]
    leadId: Optional[str] = None
    companyName: Optional[str] = None
    websiteUrl: Optional[str] = None
    normalizedDomain: Optional[str] = None
    message: str
    missingFields: list[str] = Field(default_factory=list)


class PipelineSummary(BaseModel):
    processing: int = 0
    needs_attention: int = 0
    brief_ready: int = 0
    site_generated: int = 0
    ready_to_publish: int = 0
    published: int = 0


class LeadListResponse(BaseModel):
    items: list[LeadListItem]
    pagination: dict[str, int]
    pipelineSummary: Optional[PipelineSummary] = None


class LeadActionResponse(BaseModel):
    lead: LeadDetail
    created: bool
    merged: bool
    jobId: Optional[str] = None
    message: str


class LeadImportResponse(BaseModel):
    job: JobSummary
    items: list[ImportRowResult]
    totalRows: int
    createdCount: int
    mergedCount: int
    failedCount: int
    leadIds: list[str]
