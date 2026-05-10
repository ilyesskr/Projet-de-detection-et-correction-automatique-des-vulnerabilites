import { apiClient } from "@/lib/apiClient";
import type { AuditLog, Page } from "@/api/types";

export interface ListAuditLogsParams {
  limit?: number;
  offset?: number;
  action?: string;
  actor?: string;
  entity_id?: string;
}

export async function listAuditLogs(
  params: ListAuditLogsParams = {},
): Promise<Page<AuditLog>> {
  const r = await apiClient.get<Page<AuditLog>>("/audit-logs", { params });
  return r.data;
}
