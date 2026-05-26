from pydantic import BaseModel, Field

from app.schemas.lead import JobSummary


class JobResponse(BaseModel):
    job: JobSummary
    leadIds: list[str]
    metadata: dict[str, object] = Field(default_factory=dict)


class JobQueueHealthItem(BaseModel):
    id: str
    jobType: str
    status: str
    progress: int
    step: str
    errorMessage: str | None = None
    leadIds: list[str] = Field(default_factory=list)
    retryCount: int = 0
    retryOfJobId: str | None = None
    stalled: bool = False
    createdAt: str
    updatedAt: str


class JobQueueHealthResponse(BaseModel):
    totalJobs: int
    queuedJobs: int
    runningJobs: int
    failedJobs: int
    completedJobs: int
    stalledJobs: int
    backlogJobs: int
    byType: dict[str, int] = Field(default_factory=dict)
    stalledItems: list[JobQueueHealthItem] = Field(default_factory=list)
    failedItems: list[JobQueueHealthItem] = Field(default_factory=list)
    updatedAt: str
