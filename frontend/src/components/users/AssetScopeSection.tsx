import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, ShieldCheck, X } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import { ErrorState } from "@/components/feedback/ErrorState";
import { AssetCombobox } from "@/components/assets/AssetCombobox";

import {
  grantUserAssetScope,
  revokeUserAssetScope,
} from "@/api/users";
import { useUserAssetScope } from "@/hooks/queries/useUsers";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { dash } from "@/lib/format";
import type { Asset, User } from "@/api/types";

interface AssetScopeSectionProps {
  user: User;
}

/**
 * Per-user list of explicitly-scoped assets, plus add/remove controls.
 *
 * Superusers bypass scope server-side, so we surface a banner and
 * skip rendering the scope controls — there's nothing for the admin
 * to configure here. Mirrors `apply_asset_scope` / `is_superuser` on
 * the backend so the UX explains what the data actually means.
 */
export function AssetScopeSection({ user }: AssetScopeSectionProps) {
  const queryClient = useQueryClient();
  const scopeQuery = useUserAssetScope(user.is_superuser ? undefined : user.id);

  const [pendingAsset, setPendingAsset] = useState<Asset | null>(null);

  const scopedIds = useMemo(
    () => new Set((scopeQuery.data ?? []).map((a) => a.id)),
    [scopeQuery.data],
  );

  const grantMutation = useMutationWithToast({
    mutationFn: (assetId: string) =>
      grantUserAssetScope(user.id, assetId),
    successMessage: "Asset scope granted",
    onSuccess: () => {
      setPendingAsset(null);
      queryClient.invalidateQueries({
        queryKey: ["users", "asset-scope", user.id],
      });
    },
  });

  const revokeMutation = useMutationWithToast({
    mutationFn: (assetId: string) =>
      revokeUserAssetScope(user.id, assetId),
    successMessage: "Asset scope revoked",
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["users", "asset-scope", user.id],
      });
    },
  });

  if (user.is_superuser) {
    return (
      <Alert>
        <ShieldCheck className="h-4 w-4" />
        <AlertTitle>Superuser — scope bypassed</AlertTitle>
        <AlertDescription>
          Superusers have access to every asset in the system. Asset
          scope rows are not enforced for this account.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <p className="text-xs text-muted-foreground mb-1.5">
            Add asset to scope
          </p>
          <AssetCombobox
            value={pendingAsset?.id}
            onChange={(a) => setPendingAsset(a)}
            excludeIds={scopedIds}
          />
        </div>
        <Button
          type="button"
          disabled={!pendingAsset || grantMutation.isPending}
          onClick={() => pendingAsset && grantMutation.mutate(pendingAsset.id)}
        >
          {grantMutation.isPending && (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          )}
          Grant
        </Button>
      </div>

      {scopeQuery.isError ? (
        <ErrorState
          error={scopeQuery.error}
          onRetry={() => scopeQuery.refetch()}
          title="Couldn't load asset scope"
        />
      ) : scopeQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-9" />
          ))}
        </div>
      ) : scopeQuery.data && scopeQuery.data.length > 0 ? (
        <ul className="divide-y divide-slate-800/60 border border-slate-800 rounded-md">
          {scopeQuery.data.map((a) => (
            <li
              key={a.id}
              className="flex items-center justify-between px-3 py-2"
            >
              <div className="min-w-0">
                <div className="text-sm text-slate-100 truncate">
                  {a.hostname || a.wazuh_agent_id}
                </div>
                <div className="text-xs text-muted-foreground font-mono truncate">
                  {a.wazuh_agent_id}
                  {a.ip_address ? ` · ${a.ip_address}` : ""}
                  {` · ${dash(a.os_name)}`}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => revokeMutation.mutate(a.id)}
                disabled={revokeMutation.isPending}
                aria-label={`Revoke ${a.hostname || a.wazuh_agent_id}`}
              >
                <X className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          No assets scoped. Without at least one asset granted, this
          user cannot see anything in the platform.
        </p>
      )}
    </div>
  );
}
