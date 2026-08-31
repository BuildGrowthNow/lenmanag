from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

GenerationRunStatus = Literal[
    "queued", "running", "partial", "completed", "failed", "superseded", "cancelled"
]
VariantRunStatus = Literal[
    "pending", "generating_brief", "generating_site", "compiling",
    "capturing_screenshot", "runtime_qa", "completed", "failed", "superseded"
]


class GenerationRunSnapshot(BaseModel):
    leadId: str
    leadVersion: int | None = None
    extractionId: str
    extractionVersion: int
    analysisId: str | None = None
    analysisVersion: int | None = None
    briefId: str
    briefVersion: int
    brandRevision: int = 1
    brandSnapshotHash: str
    brandSnapshot: dict[str, Any] = Field(default_factory=dict)
    approvedImageInventory: list[dict[str, Any]] = Field(default_factory=list)
    rejectedImages: list[str] = Field(default_factory=list)
    operatorInstructions: str | None = None
    generationTypes: list[str] = Field(default_factory=list)
    variantStrategies: list[dict[str, Any]] = Field(default_factory=list)
    generatorVersion: str = "generation-run-v1"
    promptVersion: str = "master-brief-v1"


class GenerationRun(BaseModel):
    id: str
    leadId: str
    jobId: str
    status: GenerationRunStatus
    snapshot: GenerationRunSnapshot
    generationInputHash: str
    requestedBy: str | None = None
    operatorInstructions: str | None = None
    variantBriefs: list[dict[str, Any]] = Field(default_factory=list)
    variantResults: list[dict[str, Any]] = Field(default_factory=list)
    createdAt: datetime
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    supersededByRunId: str | None = None
    supersededReason: str | None = None
