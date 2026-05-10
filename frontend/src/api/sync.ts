import { apiClient } from "@/lib/apiClient";
import type { SyncResult } from "@/api/types";

export async function syncAgents(): Promise<SyncResult> {
  const r = await apiClient.post<SyncResult>("/sync/wazuh/agents");
  return r.data;
}

export async function syncVulnerabilities(): Promise<SyncResult> {
  const r = await apiClient.post<SyncResult>("/sync/wazuh/vulnerabilities");
  return r.data;
}
