import { cn } from "@/lib/utils";

const SEVERITY_CLASS: Record<string, string> = {
  critical: "bg-status-critical/15 text-status-critical border-status-critical/40",
  high:     "bg-status-high/15 text-status-high border-status-high/40",
  medium:   "bg-status-medium/15 text-status-medium border-status-medium/40",
  low:      "bg-status-low/15 text-status-low border-status-low/40",
};

interface SeverityBadgeProps {
  severity: string;
}

/**
 * Badge for vulnerability severity. The tailwind `status` palette is
 * spec §3 — keeping the color map here means a re-skin happens in one
 * file.
 *
 * Wazuh occasionally emits values outside the documented vocabulary
 * (e.g., "unknown" or "—"). Those fall through to the muted style so
 * the row still renders.
 */
export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const cls =
    SEVERITY_CLASS[severity?.toLowerCase()] ??
    "bg-slate-700/40 text-slate-300 border-slate-600";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium uppercase tracking-wide",
        cls,
      )}
    >
      {severity || "unknown"}
    </span>
  );
}
