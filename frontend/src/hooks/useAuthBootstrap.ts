import { useEffect } from "react";

import { apiClient } from "@/lib/apiClient";
import { useAuthStore, type UserSelf } from "@/stores/auth";

/**
 * Run once at app start to recover the session from a prior tab.
 *
 * Logic:
 * - No token in storage → mark unauthenticated; ProtectedRoute will
 *   bounce protected routes to /login.
 * - Token present → mark `authenticating` and call `/auth/me`. On
 *   success, hydrate user + permissions. On 401, the apiClient
 *   interceptor already cleared the session and redirected; no extra
 *   work here.
 *
 * Anything other than 401 (network down, 5xx) clears the local session.
 * That is stricter than optimistic offline auth, but safer for an
 * enterprise console because we never render protected pages without
 * fresh user/permission data from the backend.
 */
export function useAuthBootstrap(): void {
  useEffect(() => {
    const { token, status, setUser, setStatus, clearSession } =
      useAuthStore.getState();

    if (status !== "idle") return;

    if (!token) {
      setStatus("unauthenticated");
      return;
    }

    setStatus("authenticating");
    apiClient
      .get<UserSelf>("/auth/me")
      .then((resp) => setUser(resp.data))
      .catch((err: { status?: number }) => {
        if (err.status === 401) {
          // Already cleared by the 401 interceptor — nothing to do.
          return;
        }
        // Conservative failure path: do not keep a token if we could
        // not refresh the user/permission envelope from the backend.
        clearSession();
      });
  }, []);
}
