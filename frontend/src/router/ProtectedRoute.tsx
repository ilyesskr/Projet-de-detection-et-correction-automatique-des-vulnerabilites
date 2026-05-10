import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuthStore } from "@/stores/auth";
import { Skeleton } from "@/components/ui/skeleton";

interface ProtectedRouteProps {
  /**
   * Optional permission string (e.g., "users:manage"). When set, an
   * authenticated user without the permission sees a 403 page instead
   * of the route's content. Backend enforcement is the real gate; this
   * is UX only.
   */
  requiredPermission?: string;
  /**
   * Inline element instead of `<Outlet />` — supports both
   * `<ProtectedRoute><Page /></ProtectedRoute>` and the layout-route
   * pattern `<Route element={<ProtectedRoute />}><Route .../></Route>`.
   */
  children?: ReactNode;
}

export default function ProtectedRoute({
  requiredPermission,
  children,
}: ProtectedRouteProps) {
  const status = useAuthStore((s) => s.status);
  const permissions = useAuthStore((s) => s.permissions);
  const location = useLocation();

  // App-mount bootstrap is in flight (or hasn't run yet on a fresh tab) —
  // hold the route render rather than flashing /login. Skeleton is
  // intentionally a single block; layout shell lands in Phase 3.
  if (status === "idle" || status === "authenticating") {
    return (
      <div className="p-8">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full mt-4" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    // Remember where the user was trying to go so LoginPage can bounce
    // them back after a successful sign-in.
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  }

  if (
    requiredPermission &&
    !permissions.includes(requiredPermission)
  ) {
    return <AccessDenied permission={requiredPermission} />;
  }

  return children ?? <Outlet />;
}

function AccessDenied({ permission }: { permission: string }) {
  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-semibold tracking-tight">Access denied</h1>
      <p className="text-sm text-muted-foreground mt-2">
        You do not have the <code className="font-mono">{permission}</code>{" "}
        permission required to view this page. Ask an administrator if you
        believe this is wrong.
      </p>
    </div>
  );
}
