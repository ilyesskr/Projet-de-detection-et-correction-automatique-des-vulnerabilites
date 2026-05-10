import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listVulnerabilities, type ListVulnsParams } from "@/api/vulnerabilities";

export function useVulnerabilities(params: ListVulnsParams) {
  return useQuery({
    queryKey: ["vulnerabilities", "list", params],
    queryFn: () => listVulnerabilities(params),
    placeholderData: keepPreviousData,
  });
}
