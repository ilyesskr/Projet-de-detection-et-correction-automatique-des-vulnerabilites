import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  getRemediationJob,
  listRemediationJobs,
  type ListJobsParams,
} from "@/api/remediation";

export function useRemediationJobs(params: ListJobsParams) {
  return useQuery({
    queryKey: ["remediation", "list", params],
    queryFn: () => listRemediationJobs(params),
    placeholderData: keepPreviousData,
  });
}

export function useRemediationJob(id: string | undefined) {
  return useQuery({
    queryKey: ["remediation", "detail", id],
    queryFn: () => getRemediationJob(id!),
    enabled: !!id,
  });
}
