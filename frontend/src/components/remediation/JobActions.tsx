import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, PlayCircle, RefreshCcw, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";

import {
  approveRemediationJob,
  launchRemediationJob,
  refreshRemediationJob,
  verifyRemediationJob,
} from "@/api/remediation";
import type { RemediationJob } from "@/api/types";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { usePermissions } from "@/hooks/usePermissions";

interface JobActionsProps {
  job: RemediationJob;
}

/**
 * Action buttons for a remediation job. Each button is gated by BOTH:
 * - the user's permission (matches spec §8.6's permission→action map), and
 * - the current job status (only certain transitions are valid).
 *
 * The backend enforces both rules independently — if a 409/403 comes
 * back anyway, the toast surfaces it. Disabling rather than hiding the
 * mutating buttons during in-flight is a deliberate choice: the user
 * sees the spinner inline instead of buttons rearranging.
 */
export function JobActions({ job }: JobActionsProps) {
  const { has } = usePermissions();
  const queryClient = useQueryClient();

  function refreshAfter(mutated: RemediationJob) {
    queryClient.setQueryData<RemediationJob>(
      ["remediation", "detail", mutated.id],
      mutated,
    );
    queryClient.invalidateQueries({ queryKey: ["remediation"] });
    queryClient.invalidateQueries({
      queryKey: ["audit-logs", "by-entity", mutated.id],
    });
  }

  const approveMutation = useMutationWithToast({
    mutationFn: () => approveRemediationJob(job.id),
    successMessage: "Job approved",
    onSuccess: refreshAfter,
  });
  const launchMutation = useMutationWithToast({
    mutationFn: () => launchRemediationJob(job.id),
    successMessage: "Launch requested",
    onSuccess: refreshAfter,
  });
  const refreshMutation = useMutationWithToast({
    mutationFn: () => refreshRemediationJob(job.id),
    successMessage: "Status refreshed",
    onSuccess: refreshAfter,
  });
  const verifyMutation = useMutationWithToast({
    mutationFn: () => verifyRemediationJob(job.id),
    successMessage: "Verification triggered",
    onSuccess: refreshAfter,
  });

  const canApprove = has("remediation:approve") && job.status === "pending_approval";
  const canLaunch  = has("remediation:launch")  && job.status === "approved";
  const canRefresh = has("remediation:launch")  && job.status === "running";
  const canVerify  = has("remediation:verify")  && job.status === "verification_pending";

  if (!canApprove && !canLaunch && !canRefresh && !canVerify) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {canApprove && (
        <Button
          onClick={() => approveMutation.mutate()}
          disabled={approveMutation.isPending}
        >
          {approveMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <ShieldCheck className="h-4 w-4 mr-2" />
          )}
          Approve
        </Button>
      )}
      {canLaunch && (
        <Button
          onClick={() => launchMutation.mutate()}
          disabled={launchMutation.isPending}
        >
          {launchMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <PlayCircle className="h-4 w-4 mr-2" />
          )}
          Launch
        </Button>
      )}
      {canRefresh && (
        <Button
          variant="outline"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
        >
          {refreshMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <RefreshCcw className="h-4 w-4 mr-2" />
          )}
          Refresh
        </Button>
      )}
      {canVerify && (
        <Button
          onClick={() => verifyMutation.mutate()}
          disabled={verifyMutation.isPending}
        >
          {verifyMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4 mr-2" />
          )}
          Verify
        </Button>
      )}
    </div>
  );
}
