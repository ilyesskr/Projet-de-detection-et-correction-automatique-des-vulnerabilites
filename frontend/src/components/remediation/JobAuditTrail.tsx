import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";

import { ErrorState } from "@/components/feedback/ErrorState";
import { useEntityAuditLogs } from "@/hooks/queries/useEntityAuditLogs";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AuditLog } from "@/api/types";

interface JobAuditTrailProps {
  jobId: string;
}

export function JobAuditTrail({ jobId }: JobAuditTrailProps) {
  const query = useEntityAuditLogs(jobId, 50);

  if (query.isError) {
    return (
      <ErrorState
        error={query.error}
        onRetry={() => query.refetch()}
        title="Couldn't load audit trail"
      />
    );
  }

  if (query.isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );
  }

  const items = query.data?.items ?? [];
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No audit entries for this job yet.
      </p>
    );
  }

  return (
    <ul className="space-y-1 divide-y divide-slate-800/60 border border-slate-800 rounded-md">
      {items.map((entry) => (
        <AuditRow key={entry.id} entry={entry} />
      ))}
    </ul>
  );
}

function AuditRow({ entry }: { entry: AuditLog }) {
  const [expanded, setExpanded] = useState(false);
  const hasContext = entry.context && Object.keys(entry.context).length > 0;

  return (
    <li className="px-3 py-2 text-sm">
      <button
        type="button"
        onClick={() => hasContext && setExpanded((v) => !v)}
        className={cn(
          "w-full text-left flex items-center gap-2",
          hasContext && "cursor-pointer",
        )}
      >
        {hasContext ? (
          expanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
          )
        ) : (
          <span className="w-3 shrink-0" />
        )}
        <span
          className={cn(
            "inline-flex h-1.5 w-1.5 rounded-full shrink-0",
            entry.success ? "bg-status-fixed" : "bg-status-failed",
          )}
          aria-hidden
        />
        <span className="font-medium text-slate-100">{entry.action}</span>
        <span className="text-muted-foreground">by {entry.actor}</span>
        <span className="text-xs text-muted-foreground ml-auto whitespace-nowrap">
          {formatDateTime(entry.created_at)}
        </span>
      </button>
      {expanded && hasContext && (
        <pre className="mt-2 ml-5 text-xs bg-slate-950/60 border border-slate-800 rounded p-2 overflow-x-auto">
          {JSON.stringify(entry.context, null, 2)}
        </pre>
      )}
    </li>
  );
}
