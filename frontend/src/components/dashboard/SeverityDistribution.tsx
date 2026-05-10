import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"] as const;
type Sev = (typeof SEVERITY_ORDER)[number];

const SEV_BG: Record<Sev, string> = {
  critical: "bg-status-critical",
  high: "bg-status-high",
  medium: "bg-status-medium",
  low: "bg-status-low",
};

const SEV_LABEL: Record<Sev, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

interface SeverityDistributionProps {
  counts: Record<string, number> | undefined;
  loading?: boolean;
}

/**
 * Stacked horizontal bar of open vulnerability severity. Empty state
 * (all zeros) renders an explicit "no open vulnerabilities" line so
 * the user doesn't see a blank track and wonder if it's loading.
 */
export function SeverityDistribution({
  counts,
  loading,
}: SeverityDistributionProps) {
  if (loading || !counts) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-3 w-full" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {SEVERITY_ORDER.map((s) => (
            <Skeleton key={s} className="h-8" />
          ))}
        </div>
      </div>
    );
  }

  const total = SEVERITY_ORDER.reduce((acc, s) => acc + (counts[s] ?? 0), 0);

  return (
    <div className="space-y-3">
      {total === 0 ? (
        <div className="h-3 rounded-full bg-slate-800/60" />
      ) : (
        <div
          className="h-3 rounded-full overflow-hidden flex bg-slate-800/60"
          role="img"
          aria-label={`${total} open vulnerabilities`}
        >
          {SEVERITY_ORDER.map((s) => {
            const c = counts[s] ?? 0;
            if (c === 0) return null;
            const pct = (c / total) * 100;
            return (
              <span
                key={s}
                className={cn("h-full", SEV_BG[s])}
                style={{ width: `${pct}%` }}
                title={`${SEV_LABEL[s]}: ${c}`}
              />
            );
          })}
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {SEVERITY_ORDER.map((s) => (
          <div
            key={s}
            className="rounded-md border border-slate-800 px-3 py-2 flex items-center justify-between"
          >
            <span className="flex items-center gap-2 text-xs text-muted-foreground">
              <span
                className={cn("h-2 w-2 rounded-full", SEV_BG[s])}
                aria-hidden
              />
              {SEV_LABEL[s]}
            </span>
            <span className="text-sm font-semibold text-slate-100">
              {counts[s] ?? 0}
            </span>
          </div>
        ))}
      </div>
      {total === 0 && (
        <p className="text-xs text-muted-foreground">
          No open vulnerabilities reported.
        </p>
      )}
    </div>
  );
}
