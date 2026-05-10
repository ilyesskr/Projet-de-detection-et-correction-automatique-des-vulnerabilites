import { apiClient } from "@/lib/apiClient";
import type {
  Page,
  Severity,
  Vulnerability,
  VulnStatus,
} from "@/api/types";

export interface ListVulnsParams {
  limit?: number;
  offset?: number;
  asset_id?: string;
  severity?: Severity;
  status?: VulnStatus;
  cve?: string;
}

export async function listVulnerabilities(
  params: ListVulnsParams = {},
): Promise<Page<Vulnerability>> {
  const r = await apiClient.get<Page<Vulnerability>>("/vulnerabilities", {
    params,
  });
  return r.data;
}
