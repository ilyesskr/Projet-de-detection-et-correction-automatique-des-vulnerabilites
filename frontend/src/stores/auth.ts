import { create } from "zustand";

import type { components } from "@/types/api";

/**
 * Auth store. Single source of truth for "who is logged in and what can they do".
 *
 * Design:
 * - The token is held in state AND mirrored to `sessionStorage` so a
 *   page refresh recovers the session — but only the token survives the
 *   refresh. `user`/`permissions` are re-fetched via `bootstrap()` on
 *   every page load so role or permission changes made server-side take
 *   effect on the next refresh, not at JWT expiry.
 * - `status` drives router behavior. The `'authenticating'` state during
 *   bootstrap is what stops `ProtectedRoute` from briefly redirecting to
 *   /login on a refresh while we're still waiting on /auth/me.
 * - `apiClient` reads `getState().token` at request time, so token
 *   rotation does not require client reconstruction. The store does NOT
 *   import `apiClient` — components own the network calls and feed
 *   results back via `setSession` / `clearSession`. Keeps the cycle
 *   broken and the store independently testable.
 *
 * Storage key uses the `pa.` prefix so multiple frontends in the same
 * browser origin do not collide.
 */

export const TOKEN_STORAGE_KEY = "pa.auth.token";

export type UserSelf = components["schemas"]["UserSelf"];

export type AuthStatus =
  | "idle"            // never attempted bootstrap
  | "authenticating"  // /auth/me in flight (refresh path)
  | "authenticated"
  | "unauthenticated";

interface AuthState {
  token: string | null;
  user: UserSelf | null;
  permissions: string[];
  status: AuthStatus;

  /** Persist token + user; called from LoginPage after a successful login. */
  setSession: (token: string, user: UserSelf) => void;
  /** Replace just the user record (e.g., after /auth/me on bootstrap). */
  setUser: (user: UserSelf) => void;
  /** Set just the status — used by bootstrap and the 401 interceptor. */
  setStatus: (status: AuthStatus) => void;
  /**
   * Stage a token before we know who it belongs to. Used by login
   * between POST /auth/login and GET /auth/me so the interceptor can
   * attach the bearer header on the second call. Persists immediately.
   */
  setToken: (token: string) => void;
  /** Wipe everything; called by logout and the 401 interceptor. */
  clearSession: () => void;
}

function loadInitialToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

const initialToken = loadInitialToken();

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  user: null,
  permissions: [],
  // If we already have a token from sessionStorage, the App's bootstrap
  // effect will validate it via /auth/me — start in 'idle' so the first
  // ProtectedRoute render does not flash a redirect before bootstrap runs.
  status: "idle",

  setSession: (token, user) => {
    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    set({
      token,
      user,
      permissions: user.permissions,
      status: "authenticated",
    });
  },

  setUser: (user) => {
    set({
      user,
      permissions: user.permissions,
      status: "authenticated",
    });
  },

  setStatus: (status) => set({ status }),

  setToken: (token) => {
    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    set({ token, status: "authenticating" });
  },

  clearSession: () => {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    set({
      token: null,
      user: null,
      permissions: [],
      status: "unauthenticated",
    });
  },
}));
