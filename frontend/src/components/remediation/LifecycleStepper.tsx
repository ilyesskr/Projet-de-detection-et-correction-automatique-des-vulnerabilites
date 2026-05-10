import {
  Check,
  ChevronRight,
  CircleSlash,
  Clock,
  XCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Horizontal stepper for the seven lifecycle states.
 *
 * Happy path is `pending_approval → approved → running →
 * verification_pending → verified_fixed`. The stepper renders that
 * path as five dots; `failed` and `cancelled` are terminal off-path
 * states rendered as a single trailing pill so the user immediately
 * sees something is wrong instead of "all dots dark".
 */

const HAPPY_PATH = [
  { key: "pending_approval",     label: "Pending"   },
  { key: "approved",             label: "Approved"  },
  { key: "running",              label: "Running"   },
  { key: "verification_pending", label: "Verifying" },
  { key: "verified_fixed",       label: "Verified"  },
] as const;
type HappyKey = (typeof HAPPY_PATH)[number]["key"];

const HAPPY_INDEX: Record<HappyKey, number> = {
  pending_approval: 0,
  approved: 1,
  running: 2,
  verification_pending: 3,
  verified_fixed: 4,
};

interface LifecycleStepperProps {
  status: string;
}

export function LifecycleStepper({ status }: LifecycleStepperProps) {
  if (status === "failed" || status === "cancelled") {
    return <TerminalState status={status} />;
  }
  const current = HAPPY_INDEX[status as HappyKey] ?? -1;

  return (
    <ol className="flex items-center gap-1.5 overflow-x-auto py-1">
      {HAPPY_PATH.map((step, i) => {
        const isCurrent = i === current;
        const isComplete = i < current;
        return (
          <li key={step.key} className="flex items-center gap-1.5 shrink-0">
            <span
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs",
                isCurrent &&
                  "bg-status-running/15 text-status-running border-status-running/40 font-medium",
                isComplete &&
                  "bg-status-fixed/15 text-status-fixed border-status-fixed/40",
                !isCurrent &&
                  !isComplete &&
                  "text-muted-foreground border-slate-800",
              )}
            >
              {isComplete ? (
                <Check className="h-3 w-3" />
              ) : isCurrent ? (
                <Clock className="h-3 w-3" />
              ) : (
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-current opacity-50"
                  aria-hidden
                />
              )}
              {step.label}
            </span>
            {i < HAPPY_PATH.length - 1 && (
              <ChevronRight className="h-3 w-3 text-slate-700" />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function TerminalState({ status }: { status: string }) {
  const isFailed = status === "failed";
  const Icon = isFailed ? XCircle : CircleSlash;
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm",
        isFailed
          ? "bg-status-failed/15 text-status-failed border-status-failed/40"
          : "bg-slate-700/40 text-slate-300 border-slate-600",
      )}
    >
      <Icon className="h-4 w-4" />
      {isFailed ? "Job failed" : "Job cancelled"}
    </div>
  );
}
