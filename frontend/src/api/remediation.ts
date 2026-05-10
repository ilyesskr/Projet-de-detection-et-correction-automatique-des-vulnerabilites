import { apiClient } from "@/lib/apiClient";
import type {
  Page,
  RemediationJob,
  RemediationJobCreate,
  RemediationStatus,
} from "@/api/types";

export interface ListJobsParams {
  limit?: number;
  offset?: number;
  status?: RemediationStatus;
  asset_id?: string;
}

export async function listRemediationJobs(
  params: ListJobsParams = {},
): Promise<Page<RemediationJob>> {
  const r = await apiClient.get<Page<RemediationJob>>("/remediation/jobs", {
    params,
  });
  return r.data;
}

export async function getRemediationJob(id: string): Promise<RemediationJob> {
  const r = await apiClient.get<RemediationJob>(`/remediation/jobs/${id}`);
  return r.data;
}

export async function createRemediationJob(
  body: RemediationJobCreate,
): Promise<RemediationJob> {
  const r = await apiClient.post<RemediationJob>("/remediation/jobs", body);
  return r.data;
}

export async function approveRemediationJob(
  id: string,
  body: { note?: string | null } = {},
): Promise<RemediationJob> {
  const r = await apiClient.post<RemediationJob>(
    `/remediation/jobs/${id}/approve`,
    body,
  );
  return r.data;
}

export async function launchRemediationJob(id: string): Promise<RemediationJob> {
  const r = await apiClient.post<RemediationJob>(
    `/remediation/jobs/${id}/launch`,
  );
  return r.data;
}

export async function refreshRemediationJob(id: string): Promise<RemediationJob> {
  const r = await apiClient.post<RemediationJob>(
    `/remediation/jobs/${id}/refresh`,
  );
  return r.data;
}

export async function verifyRemediationJob(id: string): Promise<RemediationJob> {
  const r = await apiClient.post<RemediationJob>(
    `/remediation/jobs/${id}/verify`,
  );
  return r.data;
}
