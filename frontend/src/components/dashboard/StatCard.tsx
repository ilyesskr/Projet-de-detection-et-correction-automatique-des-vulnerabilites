import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number | string | undefined;
  icon?: LucideIcon;
  loading?: boolean;
  /**
   * Severity tint applied to the value AND the icon chip.
   *   - "critical" / "high" / "medium" → status palette
   *   - "default" → neutral slate
   * Plain text classes still work via `valueClassName`.
   */
  tone?: "default" | "critical" | "high" | "medium" | "info";
  valueClassName?: string;
  hint?: string;
}

const TONE_VALUE: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "text-slate-50",
  critical: "text-status-critical",
  high: "text-status-high",
  medium: "text-status-medium",
  info: "text-status-running",
};

const TONE_CHIP: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "bg-slate-800/70 text-slate-300 border-slate-700",
  critical: "bg-status-critical/10 text-status-critical border-status-critical/40",
  high: "bg-status-high/10 text-status-high border-status-high/40",
  medium: "bg-status-medium/10 text-status-medium border-status-medium/40",
  info: "bg-status-running/10 text-status-running border-status-running/40",
};

const TONE_GLOW: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "",
  critical: "ring-1 ring-inset ring-status-critical/20",
  high: "ring-1 ring-inset ring-status-high/15",
  medium: "",
  info: "",
};

/**
 * Stat card for the dashboard grid. Tinted icon chip + value color
 * give the row visual rhythm so the eye lands on critical/high first.
 */
export function StatCard({
  label,
  value,
  icon: Icon,
  loading,
  tone = "default",
  valueClassName,
  hint,
}: StatCardProps) {
  return (
    <Card className={cn("relative overflow-hidden", TONE_GLOW[tone])}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
              {label}
            </div>
            <div className="mt-2 min-h-[2rem]">
              {loading ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <span
                  className={cn(
                    "text-2xl font-semibold tracking-tight tabular-nums",
                    TONE_VALUE[tone],
                    valueClassName,
                  )}
                >
                  {value ?? 0}
                </span>
              )}
            </div>
            {hint && (
              <p className="text-xs text-muted-foreground mt-1">{hint}</p>
            )}
          </div>
          {Icon && (
            <span
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-lg border shrink-0",
                TONE_CHIP[tone],
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
