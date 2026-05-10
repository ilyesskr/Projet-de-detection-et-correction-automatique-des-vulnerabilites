import { apiClient } from "@/lib/apiClient";
import type { HealthResponse } from "@/api/types";

export async function wazuhHealth(): Promise<HealthResponse> {
  const r = await apiClient.get<HealthResponse>(
    "/integrations/wazuh/health",
  );
  return r.data;
}

export async function ansibleHealth(): Promise<HealthResponse> {
  const r = await apiClient.get<HealthResponse>(
    "/integrations/ansible/health",
  );
  return r.data;
}
