import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCcw,
} from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ApiError } from "@/lib/apiClient";
import type { HealthResponse } from "@/api/types";

interface IntegrationCardProps {
  name: string;
  description: string;
  query: UseQueryResult<HealthResponse, unknown>;
}

/**
 * Renders a single integration's status, last-checked time, and a
 * manual refresh button. Errors expand inline to show the raw detail
 * (typically the upstream's HTTP status / message) so an operator can
 * triage without opening dev tools.
 */
export function IntegrationCard({
  name,
  description,
  query,
}: IntegrationCardProps) {
  const [errorExpanded, setErrorExpanded] = useState(false);

  const isReachable = !!query.data && !query.isError;
  const apiError = query.error as ApiError | null;
  const lastUpdated = query.dataUpdatedAt || query.errorUpdatedAt;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-base">{name}</CardTitle>
            <CardDescription className="text-xs">{description}</CardDescription>
          </div>
          <StatusPill loading={query.isLoading} reachable={isReachable} />
        </div>
      </CardHeader>
      <CardContent className="text-sm space-y-3">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {lastUpdated
              ? `Last checked ${formatDateTime(new Date(lastUpdated).toISOString())}`
              : "Never checked"}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => query.refetch()}
            disabled={query.isFetching}
          >
            {query.isFetching ? (
              <Loader2 className="h-3 w-3 mr-1.5 animate-spin" />
            ) : (
              <RefreshCcw className="h-3 w-3 mr-1.5" />
            )}
            Refresh
          </Button>
        </div>

        {query.isError && apiError && (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2">
            <button
              type="button"
              onClick={() => setErrorExpanded((v) => !v)}
              className="w-full flex items-center gap-2 text-left text-xs"
            >
              {errorExpanded ? (
                <ChevronDown className="h-3 w-3 text-destructive shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 text-destructive shrink-0" />
              )}
              <AlertTriangle className="h-3 w-3 text-destructive shrink-0" />
              <span className="text-destructive truncate">
                {apiError.detail || "Unreachable"}
              </span>
              {apiError.status > 0 && (
                <span className="text-muted-foreground ml-auto shrink-0">
                  HTTP {apiError.status}
                </span>
              )}
            </button>
            {errorExpanded && (
              <pre className="mt-2 ml-5 text-xs text-muted-foreground whitespace-pre-wrap break-words">
                {JSON.stringify(apiError, null, 2)}
              </pre>
            )}
          </div>
        )}

        {query.data?.detail && !query.isError && (
          <p className="text-xs text-muted-foreground">{query.data.detail}</p>
        )}
      </CardContent>
    </Card>
  );
}

interface StatusPillProps {
  loading: boolean;
  reachable: boolean;
}
function StatusPill({ loading, reachable }: StatusPillProps) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground border border-slate-700 rounded-md px-2 py-0.5">
        <Loader2 className="h-3 w-3 animate-spin" />
        Checking
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs rounded-md border px-2 py-0.5",
        reachable
          ? "bg-status-fixed/15 text-status-fixed border-status-fixed/40"
          : "bg-status-failed/15 text-status-failed border-status-failed/40",
      )}
    >
      {reachable ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : (
        <AlertTriangle className="h-3 w-3" />
      )}
      {reachable ? "Reachable" : "Unreachable"}
    </span>
  );
}
