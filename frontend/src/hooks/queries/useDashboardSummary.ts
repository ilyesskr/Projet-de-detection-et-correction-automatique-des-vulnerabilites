import { useQuery } from "@tanstack/react-query";

import { getDashboardSummary } from "@/api/dashboard";

/**
 * Single round-trip the home page renders from. Backend already does
 * the asset-scope filtering and the upstream reachability checks, so
 * the dashboard doesn't need a fan-out.
 */
export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    // Re-probe on focus so the integration pills don't go stale when
    // an operator switches back to the tab.
    refetchOnWindowFocus: true,
    staleTime: 30_000,
  });
}
