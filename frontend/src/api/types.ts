/**
 * Re-exports of every backend schema we use. Keeps page/hook imports
 * short — `import type { Asset } from "@/api/types"` reads better than
 * digging through the openapi-typescript output.
 */

import type { components } from "@/types/api";

export type Asset = components["schemas"]["AssetRead"];
export type Vulnerability = components["schemas"]["VulnerabilityRead"];
export type RemediationJob = components["schemas"]["RemediationJobRead"];
export type RemediationJobCreate =
  components["schemas"]["RemediationJobCreate"];
export type RemediationJobApprove =
  components["schemas"]["RemediationJobApprove"];
export type AuditLog = components["schemas"]["AuditLogRead"];
export type Role = components["schemas"]["RoleRead"];
export type User = components["schemas"]["UserRead"];
export type UserCreate = components["schemas"]["UserCreate"];
export type UserUpdate = components["schemas"]["UserUpdate"];
export type AssetScopeAssign = components["schemas"]["AssetScopeAssign"];
export type SyncResult = components["schemas"]["SyncResult"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type DashboardSummary = components["schemas"]["DashboardSummary"];

/**
 * Generic paginated envelope. The backend returns `Page[X]` for every
 * list endpoint with `{items, total, limit, offset}`.
 */
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export const REMEDIATION_ACTIONS = [
  "package_update",
  "windows_update",
  "service_restart",
  "config_change",
] as const;
export type RemediationAction = (typeof REMEDIATION_ACTIONS)[number];

export const REMEDIATION_STATUSES = [
  "pending_approval",
  "approved",
  "running",
  "verification_pending",
  "verified_fixed",
  "failed",
  "cancelled",
] as const;
export type RemediationStatus = (typeof REMEDIATION_STATUSES)[number];

export const SEVERITIES = ["critical", "high", "medium", "low"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const VULN_STATUSES = ["open", "fixed"] as const;
export type VulnStatus = (typeof VULN_STATUSES)[number];
