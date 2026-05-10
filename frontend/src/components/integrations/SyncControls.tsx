import { useQueryClient } from "@tanstack/react-query";
import { DownloadCloud, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { syncAgents, syncVulnerabilities } from "@/api/sync";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import type { SyncResult } from "@/api/types";

/**
 * Two POST buttons that pull from Wazuh into the local DB. Both are
 * synchronous from the caller's POV (the route waits for the sync to
 * finish), so we surface a numeric breakdown — created / updated /
 * unchanged / errors — in the success toast and as in-card stats.
 */
function summaryToast(label: string, r: SyncResult) {
  const parts = [
    `${r.created} created`,
    `${r.updated} updated`,
    `${r.unchanged} unchanged`,
  ];
  if (r.marked_fixed) parts.push(`${r.marked_fixed} marked fixed`);
  if (r.skipped) parts.push(`${r.skipped} skipped`);
  if (r.errors.length > 0) parts.push(`${r.errors.length} errors`);
  toast.success(`${label}: ${parts.join(" · ")}`);
}

export function SyncControls() {
  const queryClient = useQueryClient();

  const agentsMutation = useMutationWithToast<SyncResult, unknown, void>({
    mutationFn: syncAgents,
    // Skip the wrapper's default success toast — we have a richer one.
    onSuccess: (data) => {
      summaryToast("Agents sync", data);
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });

  const vulnsMutation = useMutationWithToast<SyncResult, unknown, void>({
    mutationFn: syncVulnerabilities,
    onSuccess: (data) => {
      summaryToast("Vulnerabilities sync", data);
      queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Wazuh sync</CardTitle>
        <CardDescription>
          Pull the latest agent inventory or per-asset vulnerability
          lists from Wazuh into the local database.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => agentsMutation.mutate()}
            disabled={agentsMutation.isPending}
          >
            {agentsMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <DownloadCloud className="h-4 w-4 mr-2" />
            )}
            Sync agents
          </Button>
          <Button
            variant="outline"
            onClick={() => vulnsMutation.mutate()}
            disabled={vulnsMutation.isPending}
          >
            {vulnsMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <ShieldAlert className="h-4 w-4 mr-2" />
            )}
            Sync vulnerabilities
          </Button>
        </div>

        {(agentsMutation.data || vulnsMutation.data) && (
          <div className="grid gap-2 text-sm sm:grid-cols-2">
            {agentsMutation.data && (
              <SummaryBlock label="Agents" result={agentsMutation.data} />
            )}
            {vulnsMutation.data && (
              <SummaryBlock label="Vulnerabilities" result={vulnsMutation.data} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface SummaryBlockProps {
  label: string;
  result: SyncResult;
}
function SummaryBlock({ label, result }: SummaryBlockProps) {
  return (
    <div className="rounded-md border border-slate-800 p-3 text-xs">
      <div className="font-medium text-slate-100 mb-1">{label}</div>
      <ul className="space-y-0.5 text-muted-foreground">
        <li>created: {result.created}</li>
        <li>updated: {result.updated}</li>
        <li>unchanged: {result.unchanged}</li>
        {result.marked_fixed > 0 && <li>marked fixed: {result.marked_fixed}</li>}
        {result.skipped > 0 && <li>skipped: {result.skipped}</li>}
        {result.errors.length > 0 && (
          <li className="text-destructive">errors: {result.errors.length}</li>
        )}
      </ul>
      {result.errors.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-destructive">
            Show errors
          </summary>
          <ul className="mt-1 text-xs text-destructive/90 list-disc pl-4">
            {result.errors.slice(0, 5).map((e, i) => (
              <li key={i} className="break-words">
                {e}
              </li>
            ))}
            {result.errors.length > 5 && (
              <li>… and {result.errors.length - 5} more</li>
            )}
          </ul>
        </details>
      )}
    </div>
  );
}
