import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listAuditLogs, type ListAuditLogsParams } from "@/api/audit";

/**
 * Generic audit-logs list hook used by the audit page. The
 * single-entity variant is `useEntityAuditLogs` — kept separate
 * because its query key shape differs (entity-id-first).
 */
export function useAuditLogs(params: ListAuditLogsParams) {
  return useQuery({
    queryKey: ["audit-logs", "list", params],
    queryFn: () => listAuditLogs(params),
    placeholderData: keepPreviousData,
  });
}
