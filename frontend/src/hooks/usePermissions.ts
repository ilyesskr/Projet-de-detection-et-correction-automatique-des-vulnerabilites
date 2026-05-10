import { useMemo } from "react";

import { useAuthStore } from "@/stores/auth";

/**
 * Permission selector hook.
 *
 * `has(p)` and `hasAny(ps)` answer the question "should I render this UI?"
 * Backend permission checks remain the real security control — this hook
 * exists so we don't render disabled buttons the user cannot click.
 *
 * Superusers bypass scope and permission checks server-side, so they get
 * `true` for any query here. Mirrors the backend rule (`apply_asset_scope`
 * + `is_superuser`) and keeps admin sessions from looking under-privileged.
 */

export interface PermissionsApi {
  has: (permission: string) => boolean;
  hasAny: (permissions: readonly string[]) => boolean;
}

export function usePermissions(): PermissionsApi {
  const permissions = useAuthStore((s) => s.permissions);
  const isSuperuser = useAuthStore((s) => s.user?.is_superuser ?? false);

  return useMemo<PermissionsApi>(() => {
    const set = new Set(permissions);
    return {
      has: (p) => isSuperuser || set.has(p),
      hasAny: (ps) => isSuperuser || ps.some((p) => set.has(p)),
    };
  }, [permissions, isSuperuser]);
}
