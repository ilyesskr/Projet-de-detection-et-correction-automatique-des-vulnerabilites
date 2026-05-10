import { useState } from "react";
import { ChevronDown, ChevronRight, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

import { PageHeader } from "@/components/layout/PageHeader";
import { Pagination } from "@/components/data/Pagination";
import { ErrorState } from "@/components/feedback/ErrorState";

import { useAuditLogs } from "@/hooks/queries/useAuditLogs";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AuditLog } from "@/api/types";

const PAGE_SIZE = 50;

export default function AuditPage() {
  const [actionInput, setActionInput] = useState("");
  const [actorInput, setActorInput] = useState("");
  const [entityIdInput, setEntityIdInput] = useState("");
  const [offset, setOffset] = useState(0);

  const debouncedAction = useDebouncedValue(actionInput, 300);
  const debouncedActor = useDebouncedValue(actorInput, 300);
  const debouncedEntity = useDebouncedValue(entityIdInput, 300);

  const query = useAuditLogs({
    limit: PAGE_SIZE,
    offset,
    action: debouncedAction || undefined,
    actor: debouncedActor || undefined,
    entity_id: debouncedEntity || undefined,
  });

  const filtersActive = !!(actionInput || actorInput || entityIdInput);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Audit logs"
        description="Append-only history of every actor + action across the platform."
      />

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <Input
          value={actionInput}
          onChange={(e) => {
            setActionInput(e.target.value);
            setOffset(0);
          }}
          placeholder="Action (exact)"
          className="max-w-[200px] font-mono text-sm"
        />
        <Input
          value={actorInput}
          onChange={(e) => {
            setActorInput(e.target.value);
            setOffset(0);
          }}
          placeholder="Actor"
          className="max-w-[160px] text-sm"
        />
        <Input
          value={entityIdInput}
          onChange={(e) => {
            setEntityIdInput(e.target.value);
            setOffset(0);
          }}
          placeholder="Entity id"
          className="max-w-[260px] font-mono text-sm"
        />
        {filtersActive && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setActionInput("");
              setActorInput("");
              setEntityIdInput("");
              setOffset(0);
            }}
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't load audit logs"
        />
      ) : query.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10" />
          ))}
        </div>
      ) : query.data?.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No audit entries match these filters.
        </p>
      ) : (
        <>
          <ul className="divide-y divide-slate-800/60 border border-slate-800 rounded-md">
            {query.data?.items.map((entry) => (
              <AuditRow key={entry.id} entry={entry} />
            ))}
          </ul>
          <Pagination
            total={query.data?.total ?? 0}
            limit={PAGE_SIZE}
            offset={offset}
            onChange={({ offset }) => setOffset(offset)}
          />
        </>
      )}
    </div>
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
        <span className="font-medium text-slate-100 shrink-0">
          {entry.action}
        </span>
        <span className="text-muted-foreground shrink-0">by {entry.actor}</span>
        {entry.entity_type && (
          <span className="text-muted-foreground text-xs shrink-0">
            on {entry.entity_type}
            {entry.entity_id ? ` ${entry.entity_id.slice(0, 8)}…` : ""}
          </span>
        )}
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
