import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ApiError } from "@/lib/apiClient";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  /** Title overrides the default; useful for "Couldn't load assets". */
  title?: string;
}

export function ErrorState({ error, onRetry, title }: ErrorStateProps) {
  const apiError = error as ApiError | null;
  const detail =
    apiError?.detail ??
    (error instanceof Error ? error.message : "Something went wrong.");

  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 flex items-start gap-3">
      <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-100">
          {title ?? "Couldn't load this content"}
        </p>
        <p className="text-xs text-muted-foreground mt-1 break-words">
          {detail}
        </p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={onRetry}
          >
            Retry
          </Button>
        )}
      </div>
    </div>
  );
}
