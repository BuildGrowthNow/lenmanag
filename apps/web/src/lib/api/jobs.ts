import { request, safeRequest } from "@/lib/api/client";
import type { JobQueueHealthResponse, JobResponse, JobRetryPayload } from "@/lib/types";

export async function getJob(jobId: string): Promise<JobResponse | null> {
  return safeRequest<JobResponse | null>(`/api/jobs/${jobId}`, null);
}

export async function getQueueHealth(): Promise<JobQueueHealthResponse> {
  return safeRequest<JobQueueHealthResponse>("/api/jobs/health", {
    totalJobs: 0,
    queuedJobs: 0,
    runningJobs: 0,
    failedJobs: 0,
    completedJobs: 0,
    stalledJobs: 0,
    backlogJobs: 0,
    byType: {},
    stalledItems: [],
    failedItems: [],
    queuedItems: [],
    updatedAt: new Date(0).toISOString(),
  });
}

export async function retryJob(jobId: string, payload: JobRetryPayload = {}): Promise<JobResponse> {
  return request<JobResponse>(`/api/jobs/${jobId}/retry`, { method: "POST", body: payload });
}
