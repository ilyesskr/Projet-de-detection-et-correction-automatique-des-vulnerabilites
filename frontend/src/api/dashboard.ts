import { apiClient } from "@/lib/apiClient";
import type { DashboardSummary } from "@/api/types";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const r = await apiClient.get<DashboardSummary>("/dashboard/summary");
  return r.data;
}
