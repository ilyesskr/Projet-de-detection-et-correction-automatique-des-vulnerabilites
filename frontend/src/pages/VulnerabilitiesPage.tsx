import { useState } from "react";
import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Pagination } from "@/components/data/Pagination";
import { ErrorState } from "@/components/feedback/ErrorState";
import { SeverityBadge } from "@/components/badges/SeverityBadge";
import { CreateJobDialog } from "@/components/remediation/CreateJobDialog";

import { useVulnerabilities } from "@/hooks/queries/useVulnerabilities";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { usePermissions } from "@/hooks/usePermissions";
import { dash } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  SEVERITIES,
  type Severity,
  type Vulnerability,
  VULN_STATUSES,
  type VulnStatus,
} from "@/api/types";

const PAGE_SIZE = 25;

export default function VulnerabilitiesPage() {
  const { has } = usePermissions();

  const [severity, setSeverity] = useState<Severity | undefined>();
  const [status, setStatus] = useState<VulnStatus | undefined>();
  const [cveInput, setCveInput] = useState("");
  const [assetInput, setAssetInput] = useState("");
  const [offset, setOffset] = useState(0);

  const debouncedCve = useDebouncedValue(cveInput, 300);
  const debouncedAsset = useDebouncedValue(assetInput, 300);

  const query = useVulnerabilities({
    limit: PAGE_SIZE,
    offset,
    severity,
    status,
    cve: debouncedCve || undefined,
    asset_id: debouncedAsset || undefined,
  });

  const [createTarget, setCreateTarget] = useState<{
    assetId: string;
    vulnId: string;
    label: string;
  } | null>(null);

  const columns: Column<Vulnerability>[] = [
    { header: "CVE",       cell: (v) => <span className="font-mono text-xs">{v.cve}</span> },
    { header: "Severity",  cell: (v) => <SeverityBadge severity={v.severity} /> },
    { header: "Asset",     cell: (v) => <span className="font-mono text-xs">{v.asset_id.slice(0, 8)}…</span> },
    { header: "Package",   cell: (v) => dash(v.package_name) },
    { header: "Installed", cell: (v) => <span className="font-mono text-xs">{dash(v.installed_version)}</span> },
    { header: "Fixed in",  cell: (v) => <span className="font-mono text-xs">{dash(v.fixed_version)}</span> },
    { header: "Status",    cell: (v) => v.status },
  ];

  function resetFilters() {
    setSeverity(undefined);
    setStatus(undefined);
    setCveInput("");
    setAssetInput("");
    setOffset(0);
  }
  const filtersActive =
    severity || status || cveInput || assetInput;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Vulnerabilities"
        description="Open and historical CVEs reported by Wazuh."
      />

      {/* Severity chip row */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-xs text-muted-foreground mr-1">Severity:</span>
        {SEVERITIES.map((s) => {
          const selected = severity === s;
          return (
            <button
              key={s}
              type="button"
              onClick={() => {
                setSeverity(selected ? undefined : s);
                setOffset(0);
              }}
              className={cn(
                "px-2 py-1 rounded-md text-xs uppercase tracking-wide border transition-colors",
                selected
                  ? "bg-slate-800 border-slate-600 text-slate-50"
                  : "border-slate-800 text-muted-foreground hover:text-slate-200",
              )}
            >
              {s}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <div className="relative max-w-xs flex-1 min-w-[180px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={cveInput}
            onChange={(e) => {
              setCveInput(e.target.value);
              setOffset(0);
            }}
            placeholder="CVE (e.g. CVE-2024-1234)"
            className="pl-8 font-mono text-sm"
          />
        </div>
        <Input
          value={assetInput}
          onChange={(e) => {
            setAssetInput(e.target.value);
            setOffset(0);
          }}
          placeholder="Asset id"
          className="max-w-xs font-mono text-sm"
        />
        <Select
          value={status ?? "__all"}
          onValueChange={(v) => {
            setStatus(v === "__all" ? undefined : (v as VulnStatus));
            setOffset(0);
          }}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all">All statuses</SelectItem>
            {VULN_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {filtersActive && (
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't load vulnerabilities"
        />
      ) : (
        <>
          <DataTable<Vulnerability>
            columns={columns}
            rows={query.data?.items}
            loading={query.isLoading}
            rowKey={(v) => v.id}
            onRowClick={(v) => {
              if (!has("remediation:create") || v.status !== "open") return;
              setCreateTarget({
                assetId: v.asset_id,
                vulnId: v.id,
                label: v.cve,
              });
            }}
            empty="No vulnerabilities match your filters."
          />
          <Pagination
            total={query.data?.total ?? 0}
            limit={PAGE_SIZE}
            offset={offset}
            onChange={({ offset }) => setOffset(offset)}
          />
        </>
      )}

      {createTarget && (
        <CreateJobDialog
          open
          onOpenChange={(open) => {
            if (!open) setCreateTarget(null);
          }}
          assetId={createTarget.assetId}
          vulnerabilityId={createTarget.vulnId}
          contextLabel={createTarget.label}
        />
      )}
    </div>
  );
}
