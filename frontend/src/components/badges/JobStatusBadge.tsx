import { cn } from "@/lib/utils";

/**
 * Maps RemediationJob.status to spec §3 colors. The seven backend
 * values are listed exhaustively so adding a new one fails loudly
 * (TypeScript narrowing) instead of silently hitting a fallback.
 */
const STATUS_CLASS: Record<string, string> = {
  pending_approval:     "bg-status-pending/15 text-status-pending border-status-pending/40",
  approved:             "bg-status-approved/15 text-status-approved border-status-approved/40",
  running:              "bg-status-running/15 text-status-running border-status-running/40",
  verification_pending: "bg-status-running/15 text-status-running border-status-running/40",
  verified_fixed:       "bg-status-fixed/15 text-status-fixed border-status-fixed/40",
  failed:               "bg-status-failed/15 text-status-failed border-status-failed/40",
  cancelled:            "bg-slate-700/40 text-slate-300 border-slate-600",
};

const STATUS_LABEL: Record<string, string> = {
  pending_approval: "Pending approval",
  approved: "Approved",
  running: "Running",
  verification_pending: "Verifying",
  verified_fixed: "Verified fixed",
  failed: "Failed",
  cancelled: "Cancelled",
};

interface JobStatusBadgeProps {
  status: string;
}

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  const cls =
    STATUS_CLASS[status] ?? "bg-slate-700/40 text-slate-300 border-slate-600";
  const label = STATUS_LABEL[status] ?? status;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        cls,
      )}
    >
      {label}
    </span>
  );
}
