import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
  ServerCog,
  ShieldAlert,
  Wrench,
  XCircle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { PageHeader } from "@/components/layout/PageHeader";
import { ErrorState } from "@/components/feedback/ErrorState";
import { SeverityBadge } from "@/components/badges/SeverityBadge";
import { JobStatusBadge } from "@/components/badges/JobStatusBadge";
import { StatCard } from "@/components/dashboard/StatCard";
import { SeverityDistribution } from "@/components/dashboard/SeverityDistribution";

import { useDashboardSummary } from "@/hooks/queries/useDashboardSummary";
import { useVulnerabilities } from "@/hooks/queries/useVulnerabilities";
import { useRemediationJobs } from "@/hooks/queries/useRemediation";
import { useAuthStore } from "@/stores/auth";
import { dash, formatRelative } from "@/lib/format";

export default function DashboardPage() {
  const username = useAuthStore((s) => s.user?.username);
  const summaryQuery = useDashboardSummary();
  const recentVulns = useVulnerabilities({ limit: 5 });
  const recentJobs = useRemediationJobs({ limit: 5 });

  const summary = summaryQuery.data;
  const jobs = summary?.jobs_by_status ?? {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <PageHeader
        title={username ? `Welcome, ${username}` : "Dashboard"}
        description="Asset, vulnerability, and remediation posture at a glance."
      />

      {summaryQuery.isError ? (
        <ErrorState
          error={summaryQuery.error}
          onRetry={() => summaryQuery.refetch()}
          title="Couldn't load dashboard"
        />
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Assets"
              value={summary?.assets_total}
              loading={summaryQuery.isLoading}
              icon={ServerCog}
              tone="info"
              hint={
                summary
                  ? `${summary.assets_active} active`
                  : undefined
              }
            />
            <StatCard
              label="Critical vulns"
              value={summary?.vulns_open_by_severity?.critical}
              loading={summaryQuery.isLoading}
              icon={ShieldAlert}
              tone="critical"
            />
            <StatCard
              label="High vulns"
              value={summary?.vulns_open_by_severity?.high}
              loading={summaryQuery.isLoading}
              icon={ShieldAlert}
              tone="high"
            />
            <StatCard
              label="Pending approval"
              value={jobs.pending_approval}
              loading={summaryQuery.isLoading}
              icon={Wrench}
              tone="medium"
              hint={
                summary
                  ? `${jobs.running ?? 0} running · ${jobs.failed ?? 0} failed`
                  : undefined
              }
            />
          </div>

          {/* Severity distribution + integration row */}
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">
                  Open vulnerabilities by severity
                </CardTitle>
                <CardDescription>
                  Reported by Wazuh on the last sync, scoped to your
                  asset access.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SeverityDistribution
                  counts={summary?.vulns_open_by_severity}
                  loading={summaryQuery.isLoading}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Integrations</CardTitle>
                <CardDescription>Live upstream reachability.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <IntegrationRow
                  name="Wazuh"
                  reachable={summary?.wazuh_reachable}
                  loading={summaryQuery.isLoading}
                />
                <IntegrationRow
                  name="AWX"
                  reachable={summary?.awx_reachable}
                  loading={summaryQuery.isLoading}
                />
              </CardContent>
            </Card>
          </div>

          {/* Recent activity */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">
                    Recent vulnerabilities
                  </CardTitle>
                  <CardDescription>Newest detections.</CardDescription>
                </div>
                <Link
                  to="/vulnerabilities"
                  className="text-xs text-muted-foreground hover:text-slate-200 flex items-center"
                >
                  View all
                  <ChevronRight className="h-3 w-3 ml-0.5" />
                </Link>
              </CardHeader>
              <CardContent>
                {recentVulns.isError ? (
                  <ErrorState
                    error={recentVulns.error}
                    onRetry={() => recentVulns.refetch()}
                    title="Couldn't load"
                  />
                ) : recentVulns.isLoading ? (
                  <RowSkeletons />
                ) : recentVulns.data?.items.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    No vulnerabilities reported.
                  </p>
                ) : (
                  <ul className="divide-y divide-slate-800/60">
                    {recentVulns.data?.items.map((v) => (
                      <li key={v.id} className="py-2 flex items-center gap-3">
                        <SeverityBadge severity={v.severity} />
                        <Link
                          to={`/assets/${v.asset_id}`}
                          className="font-mono text-xs text-slate-200 truncate hover:underline"
                        >
                          {v.cve}
                        </Link>
                        <span className="text-xs text-muted-foreground truncate hidden sm:inline">
                          {dash(v.package_name)}
                        </span>
                        <span className="text-xs text-muted-foreground ml-auto whitespace-nowrap">
                          {formatRelative(v.created_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">
                    Recent remediation jobs
                  </CardTitle>
                  <CardDescription>Newest first.</CardDescription>
                </div>
                <Link
                  to="/remediation"
                  className="text-xs text-muted-foreground hover:text-slate-200 flex items-center"
                >
                  View all
                  <ChevronRight className="h-3 w-3 ml-0.5" />
                </Link>
              </CardHeader>
              <CardContent>
                {recentJobs.isError ? (
                  <ErrorState
                    error={recentJobs.error}
                    onRetry={() => recentJobs.refetch()}
                    title="Couldn't load"
                  />
                ) : recentJobs.isLoading ? (
                  <RowSkeletons />
                ) : recentJobs.data?.items.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    No remediation jobs yet.
                  </p>
                ) : (
                  <ul className="divide-y divide-slate-800/60">
                    {recentJobs.data?.items.map((j) => (
                      <li key={j.id} className="py-2 flex items-center gap-3">
                        <JobStatusBadge status={j.status} />
                        <Link
                          to={`/remediation/${j.id}`}
                          className="font-mono text-xs text-slate-200 hover:underline"
                        >
                          {j.id.slice(0, 8)}…
                        </Link>
                        <span className="text-xs text-muted-foreground truncate">
                          {j.action} · by {j.created_by}
                        </span>
                        <span className="text-xs text-muted-foreground ml-auto whitespace-nowrap">
                          {formatRelative(j.created_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

interface IntegrationRowProps {
  name: string;
  reachable: boolean | undefined;
  loading: boolean;
}
function IntegrationRow({ name, reachable, loading }: IntegrationRowProps) {
  return (
    <div className="flex items-center justify-between text-sm py-1">
      <span className="text-slate-200">{name}</span>
      {loading ? (
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Checking
        </span>
      ) : reachable ? (
        <span className="inline-flex items-center gap-1.5 text-xs text-status-fixed">
          <CheckCircle2 className="h-3 w-3" />
          Reachable
        </span>
      ) : reachable === false ? (
        <span className="inline-flex items-center gap-1.5 text-xs text-status-failed">
          <XCircle className="h-3 w-3" />
          Unreachable
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <AlertTriangle className="h-3 w-3" />
          Unknown
        </span>
      )}
    </div>
  );
}

function RowSkeletons() {
  return (
    <div className="space-y-2 py-1">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-6" />
      ))}
    </div>
  );
}
