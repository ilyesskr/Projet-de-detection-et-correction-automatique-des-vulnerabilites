import type { NavigateFunction } from "react-router-dom";

/**
 * Tiny registry that lets non-React modules (specifically the axios 401
 * interceptor) navigate via React Router. App registers `useNavigate()`
 * once on mount; the interceptor pulls it out when it needs to bounce
 * the user to /login.
 *
 * If the registry is empty (e.g., the interceptor fires before App
 * mounts, or in a test), we fall back to `window.location.assign` so
 * the user is still redirected — slower (full reload) but never silent.
 */

let navigateRef: NavigateFunction | null = null;

export function registerNavigator(navigate: NavigateFunction): void {
  navigateRef = navigate;
}

export function navigateTo(path: string): void {
  if (navigateRef) {
    navigateRef(path, { replace: true });
  } else if (typeof window !== "undefined") {
    window.location.assign(path);
  }
}
