import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/stores/auth";

/**
 * Returns a `logout()` handler. Wipes the auth store + sessionStorage
 * and routes to /login.
 *
 * Server-side revocation is not implemented yet — backend feature (b)
 * (refresh tokens + logout revocation) is deferred per the JWT_RBAC
 * plan. Until then, an old access token remains technically valid for
 * its full lifetime if it was captured before logout. Acceptable for
 * the first release because tokens are short-lived (60 min).
 */
export function useLogout(): () => void {
  const clearSession = useAuthStore((s) => s.clearSession);
  const navigate = useNavigate();

  return useCallback(() => {
    clearSession();
    navigate("/login", { replace: true });
  }, [clearSession, navigate]);
}
