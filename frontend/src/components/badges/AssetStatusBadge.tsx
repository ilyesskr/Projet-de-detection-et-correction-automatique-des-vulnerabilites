import { cn } from "@/lib/utils";

/**
 * Wazuh agent status. The vocabulary varies between Wazuh versions
 * ("active", "disconnected", "never_connected", "pending", ...), so
 * unknown values fall back to muted slate rather than blank.
 */
const STATUS_CLASS: Record<string, string> = {
  active:           "bg-status-fixed/15 text-status-fixed border-status-fixed/40",
  disconnected:     "bg-status-failed/15 text-status-failed border-status-failed/40",
  never_connected:  "bg-slate-700/40 text-slate-300 border-slate-600",
  pending:          "bg-status-pending/15 text-status-pending border-status-pending/40",
};

interface AssetStatusBadgeProps {
  status: string | null | undefined;
}

export function AssetStatusBadge({ status }: AssetStatusBadgeProps) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  const cls =
    STATUS_CLASS[status] ?? "bg-slate-700/40 text-slate-300 border-slate-600";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        cls,
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
