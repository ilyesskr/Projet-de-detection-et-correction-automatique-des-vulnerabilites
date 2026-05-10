import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import AssetsPage from "@/pages/AssetsPage";
import AssetDetailPage from "@/pages/AssetDetailPage";
import VulnerabilitiesPage from "@/pages/VulnerabilitiesPage";
import RemediationPage from "@/pages/RemediationPage";
import RemediationJobDetailPage from "@/pages/RemediationJobDetailPage";
import UsersPage from "@/pages/UsersPage";
import AuditPage from "@/pages/AuditPage";
import IntegrationsPage from "@/pages/IntegrationsPage";
import ProtectedRoute from "@/router/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";
import { useAuthBootstrap } from "@/hooks/useAuthBootstrap";
import { useNavigatorRegistration } from "@/hooks/useNavigatorRegistration";

/**
 * Top-level route map for the operator console. Paths come from
 * FRONTEND_SPECIFICATION §6.
 */

/**
 * Inside the router so `useNavigate` is available — `useNavigatorRegistration`
 * needs router context. Bootstrap runs here too so it doesn't depend on
 * provider order in `App.tsx`.
 */
function RouterRoot() {
  useAuthBootstrap();
  useNavigatorRegistration();

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />

          <Route path="/assets" element={<AssetsPage />} />
          <Route path="/assets/:assetId" element={<AssetDetailPage />} />

          <Route path="/vulnerabilities" element={<VulnerabilitiesPage />} />

          <Route path="/remediation" element={<RemediationPage />} />
          <Route
            path="/remediation/:jobId"
            element={<RemediationJobDetailPage />}
          />

          <Route
            path="/users"
            element={
              <ProtectedRoute requiredPermission="users:manage">
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/integrations" element={<IntegrationsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <RouterRoot />
    </BrowserRouter>
  );
}
