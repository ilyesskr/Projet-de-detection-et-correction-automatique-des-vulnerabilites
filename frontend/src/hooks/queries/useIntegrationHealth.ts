import { useQuery } from "@tanstack/react-query";

import { ansibleHealth, wazuhHealth } from "@/api/integrations";

/**
 * Integration health checks run real round-trips to Wazuh / AWX, so
 * default refetchOnWindowFocus is the right behavior — coming back to
 * the page should re-probe. Backed off retries because a flapping
 * integration shouldn't fan out three calls per render.
 */

export function useWazuhHealth() {
  return useQuery({
    queryKey: ["integrations", "wazuh", "health"],
    queryFn: wazuhHealth,
    retry: 0,
    staleTime: 15_000,
  });
}

export function useAnsibleHealth() {
  return useQuery({
    queryKey: ["integrations", "awx", "health"],
    queryFn: ansibleHealth,
    retry: 0,
    staleTime: 15_000,
  });
}
