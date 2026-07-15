import { request, safeRequest } from "@/lib/api/client";
import type { JobQueueHealthResponse, JobResponse, JobRetryPayload } from "@/lib/types";

export async function getJob(jobId: string): Promise<JobResponse | null> {
  return safeRequest<JobResponse | null>(`/api/jobs/${jobId}`, null);
}

export async function getQueueHealth(): Promise<JobQueueHealthResponse> {
  return request<JobQueueHealthResponse>("/api/jobs/health");
}

export async function retryJob(jobId: string, payload: JobRetryPayload = {}): Promise<JobResponse> {
  return request<JobResponse>(`/api/jobs/${jobId}/retry`, { method: "POST", body: payload });
}
