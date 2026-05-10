import { useQuery } from "@tanstack/react-query";

import { listAuditLogs } from "@/api/audit";

/**
 * Audit trail for a single entity (used by the job detail page).
 * Refetches on window focus by default — auditing is the kind of data
 * an operator wants to see fresh after switching tabs.
 */
export function useEntityAuditLogs(
  entityId: string | undefined,
  limit = 50,
) {
  return useQuery({
    queryKey: ["audit-logs", "by-entity", entityId, limit],
    queryFn: () => listAuditLogs({ entity_id: entityId, limit }),
    enabled: !!entityId,
  });
}
