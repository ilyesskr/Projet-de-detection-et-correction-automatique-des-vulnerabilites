import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Wrench } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Pagination } from "@/components/data/Pagination";
import { ErrorState } from "@/components/feedback/ErrorState";
import { AssetStatusBadge } from "@/components/badges/AssetStatusBadge";
import { SeverityBadge } from "@/components/badges/SeverityBadge";
import { CreateJobDialog } from "@/components/remediation/CreateJobDialog";

import {
  useAsset,
  useAssetVulnerabilities,
} from "@/hooks/queries/useAssets";
import { usePermissions } from "@/hooks/usePermissions";
import { dash, formatDateTime, formatRelative } from "@/lib/format";
import type { Vulnerability } from "@/api/types";

const VULN_PAGE_SIZE = 10;

export default function AssetDetailPage() {
  const { assetId } = useParams<{ assetId: string }>();
  const navigate = useNavigate();
  const { has } = usePermissions();

  const [vulnOffset, setVulnOffset] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForVulnId, setCreateForVulnId] = useState<string | undefined>();

  const assetQuery = useAsset(assetId);
  const vulnsQuery = useAssetVulnerabilities(assetId, {
    limit: VULN_PAGE_SIZE,
    offset: vulnOffset,
  });

  function openCreateForVuln(vulnId?: string) {
    setCreateForVulnId(vulnId);
    setCreateOpen(true);
  }

  const vulnColumns: Column<Vulnerability>[] = [
    { header: "CVE",      cell: (v) => <span className="font-mono text-xs">{v.cve}</span> },
    { header: "Severity", cell: (v) => <SeverityBadge severity={v.severity} /> },
    { header: "Package",  cell: (v) => dash(v.package_name) },
    { header: "Installed", cell: (v) => <span className="font-mono text-xs">{dash(v.installed_version)}</span> },
    { header: "Fixed in",  cell: (v) => <span className="font-mono text-xs">{dash(v.fixed_version)}</span> },
    { header: "Status",   cell: (v) => v.status },
    {
      header: "",
      className: "text-right w-32",
      cell: (v) =>
        has("remediation:create") && v.status === "open" ? (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              openCreateForVuln(v.id);
            }}
          >
            <Wrench className="h-3 w-3 mr-1.5" />
            Remediate
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <Button
        variant="ghost"
        size="sm"
        className="mb-3 -ml-2 text-muted-foreground hover:text-slate-100"
        onClick={() => navigate("/assets")}
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to assets
      </Button>

      {assetQuery.isError ? (
        <ErrorState
          error={assetQuery.error}
          onRetry={() => assetQuery.refetch()}
          title="Couldn't load asset"
        />
      ) : assetQuery.isLoading || !assetQuery.data ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32" />
        </div>
      ) : (
        <>
          <PageHeader
            title={assetQuery.data.hostname || assetQuery.data.wazuh_agent_id}
            description={`Wazuh agent ${assetQuery.data.wazuh_agent_id}`}
            actions={
              has("remediation:create") && (
                <Button onClick={() => openCreateForVuln(undefined)}>
                  <Wrench className="h-4 w-4 mr-2" />
                  Create remediation
                </Button>
              )
            }
          />

          <div className="grid gap-4 md:grid-cols-3 mb-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Identity</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1.5">
                <DetailRow label="Hostname" value={dash(assetQuery.data.hostname)} />
                <DetailRow
                  label="IP address"
                  value={dash(assetQuery.data.ip_address)}
                  mono
                />
                <DetailRow
                  label="Wazuh agent id"
                  value={assetQuery.data.wazuh_agent_id}
                  mono
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Operating system</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1.5">
                <DetailRow label="OS"       value={dash(assetQuery.data.os_name)} />
                <DetailRow label="Version"  value={dash(assetQuery.data.os_version)} />
                <DetailRow label="Platform" value={dash(assetQuery.data.os_platform)} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Wazuh agent</CardTitle>
                <CardDescription className="text-xs">
                  Reported by Wazuh on last sync.
                </CardDescription>
              </CardHeader>
              <CardContent className="text-sm space-y-1.5">
                <DetailRow
                  label="Status"
                  value={<AssetStatusBadge status={assetQuery.data.status} />}
                />
                <DetailRow
                  label="Agent version"
                  value={dash(assetQuery.data.agent_version)}
                  mono
                />
                <DetailRow
                  label="Last seen"
                  value={formatRelative(assetQuery.data.last_seen)}
                  hint={
                    assetQuery.data.last_seen
                      ? formatDateTime(assetQuery.data.last_seen)
                      : undefined
                  }
                />
              </CardContent>
            </Card>
          </div>

          <h2 className="text-lg font-semibold tracking-tight text-slate-100 mb-3">
            Vulnerabilities
          </h2>
          {vulnsQuery.isError ? (
            <ErrorState
              error={vulnsQuery.error}
              onRetry={() => vulnsQuery.refetch()}
              title="Couldn't load vulnerabilities"
            />
          ) : (
            <>
              <DataTable<Vulnerability>
                columns={vulnColumns}
                rows={vulnsQuery.data?.items}
                loading={vulnsQuery.isLoading}
                rowKey={(v) => v.id}
                empty="No vulnerabilities reported on this asset."
              />
              <Pagination
                total={vulnsQuery.data?.total ?? 0}
                limit={VULN_PAGE_SIZE}
                offset={vulnOffset}
                onChange={({ offset }) => setVulnOffset(offset)}
              />
            </>
          )}
        </>
      )}

      {assetQuery.data && (
        <CreateJobDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          assetId={assetQuery.data.id}
          vulnerabilityId={createForVulnId}
          contextLabel={
            assetQuery.data.hostname || assetQuery.data.wazuh_agent_id
          }
        />
      )}
    </div>
  );
}

interface DetailRowProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  hint?: string;
}
function DetailRow({ label, value, mono, hint }: DetailRowProps) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={mono ? "font-mono text-xs" : ""}
        title={hint}
      >
        {value}
      </span>
    </div>
  );
}
