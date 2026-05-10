import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import { toast } from "sonner";

import { navigateTo } from "@/lib/navigation";
import { useAuthStore } from "@/stores/auth";

/**
 * Centralized axios instance for every backend call.
 *
 * Token: read at request time from the auth store, NOT captured at
 * construction. Token rotation (login, logout, future refresh) does
 * not require rebuilding the client.
 *
 * Errors: every 4xx becomes `ApiError` with `{status, detail,
 * fieldErrors?}` so call sites and react-hook-form mappers don't have
 * to re-parse FastAPI's 422 envelope. 5xx and network errors flow
 * through with `detail` populated but no field-errors.
 *
 * 401 (session expired / token rejected): clear the store, toast, and
 * route to /login — except for /auth/login itself, where 401 means
 * "bad credentials" and the LoginPage owns the UX.
 */

export interface ApiError {
  status: number;
  detail: string;
  fieldErrors?: Record<string, string>;
}

const baseURL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000")
  .replace(/\/+$/, "");

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${baseURL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  // 30 s mirrors the backend's outbound timeout to Wazuh / AWX.
  timeout: 30_000,
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

apiClient.interceptors.response.use(
  (resp) => resp,
  (err: AxiosError) => {
    const apiError = normalizeError(err);
    if (apiError.status === 401 && !isLoginRequest(err.config?.url)) {
      // Don't toast if we're already unauthenticated (e.g., page-load
      // bootstrap caught an expired token — there's no UI state to lose
      // and a toast on a fresh tab would be confusing).
      const wasAuthenticated =
        useAuthStore.getState().status === "authenticated";
      useAuthStore.getState().clearSession();
      if (wasAuthenticated) {
        toast.error("Your session has expired. Please sign in again.");
      }
      navigateTo("/login");
    }
    return Promise.reject(apiError);
  },
);

function isLoginRequest(url: string | undefined): boolean {
  if (!url) return false;
  // Match both relative (`/auth/login`) and absolute URLs the user
  // could pass to apiClient.
  return url.includes("/auth/login");
}

function normalizeError(err: AxiosError): ApiError {
  if (err.response) {
    const { status, data } = err.response;
    const body = (data ?? {}) as Record<string, unknown>;
    const detail = pickDetail(body) ?? err.message ?? "Request failed";
    const fieldErrors = extractFieldErrors(body);
    return fieldErrors
      ? { status, detail, fieldErrors }
      : { status, detail };
  }
  return { status: 0, detail: err.message || "Network error" };
}

function pickDetail(body: Record<string, unknown>): string | undefined {
  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (typeof first.msg === "string") return first.msg;
  }
  return undefined;
}

function extractFieldErrors(
  body: Record<string, unknown>,
): Record<string, string> | undefined {
  const detail = body.detail;
  if (!Array.isArray(detail)) return undefined;
  const out: Record<string, string> = {};
  for (const entry of detail) {
    const e = entry as { loc?: unknown; msg?: unknown };
    if (Array.isArray(e.loc) && typeof e.msg === "string") {
      // `loc` typically looks like ["body", "password"]. Take the last
      // string segment as the field name.
      const field = [...e.loc]
        .reverse()
        .find((seg): seg is string => typeof seg === "string");
      if (field) out[field] = e.msg;
    }
  }
  return Object.keys(out).length > 0 ? out : undefined;
}
