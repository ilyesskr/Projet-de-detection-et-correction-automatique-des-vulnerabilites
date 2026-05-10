import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Pagination } from "@/components/data/Pagination";
import { ErrorState } from "@/components/feedback/ErrorState";
import { JobStatusBadge } from "@/components/badges/JobStatusBadge";

import { useRemediationJobs } from "@/hooks/queries/useRemediation";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { dash, formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  REMEDIATION_STATUSES,
  type RemediationJob,
  type RemediationStatus,
} from "@/api/types";

const PAGE_SIZE = 25;

const STATUS_LABEL: Record<RemediationStatus, string> = {
  pending_approval: "Pending",
  approved: "Approved",
  running: "Running",
  verification_pending: "Verifying",
  verified_fixed: "Verified",
  failed: "Failed",
  cancelled: "Cancelled",
};

export default function RemediationPage() {
  const navigate = useNavigate();

  const [status, setStatus] = useState<RemediationStatus | undefined>();
  const [assetInput, setAssetInput] = useState("");
  const [offset, setOffset] = useState(0);

  const debouncedAsset = useDebouncedValue(assetInput, 300);

  const query = useRemediationJobs({
    limit: PAGE_SIZE,
    offset,
    status,
    asset_id: debouncedAsset || undefined,
  });

  const columns: Column<RemediationJob>[] = [
    {
      header: "Job",
      cell: (j) => (
        <span className="font-mono text-xs">{j.id.slice(0, 8)}…</span>
      ),
    },
    { header: "Action", cell: (j) => j.action },
    { header: "Status", cell: (j) => <JobStatusBadge status={j.status} /> },
    {
      header: "AWX job",
      cell: (j) => (
        <span className="font-mono text-xs">{dash(j.awx_job_id)}</span>
      ),
    },
    { header: "Created by",  cell: (j) => j.created_by },
    { header: "Approved by", cell: (j) => dash(j.approved_by) },
    { header: "Created",     cell: (j) => formatRelative(j.created_at) },
  ];

  const filtersActive = status || assetInput;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Remediation jobs"
        description="Lifecycle of every correction request — pending → approved → running → verified."
      />

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-xs text-muted-foreground mr-1">Status:</span>
        {REMEDIATION_STATUSES.map((s) => {
          const selected = status === s;
          return (
            <button
              key={s}
              type="button"
              onClick={() => {
                setStatus(selected ? undefined : s);
                setOffset(0);
              }}
              className={cn(
                "px-2 py-1 rounded-md text-xs border transition-colors",
                selected
                  ? "bg-slate-800 border-slate-600 text-slate-50"
                  : "border-slate-800 text-muted-foreground hover:text-slate-200",
              )}
            >
              {STATUS_LABEL[s]}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <Input
          value={assetInput}
          onChange={(e) => {
            setAssetInput(e.target.value);
            setOffset(0);
          }}
          placeholder="Asset id"
          className="max-w-xs font-mono text-sm"
        />
        {filtersActive && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatus(undefined);
              setAssetInput("");
              setOffset(0);
            }}
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't load remediation jobs"
        />
      ) : (
        <>
          <DataTable<RemediationJob>
            columns={columns}
            rows={query.data?.items}
            loading={query.isLoading}
            rowKey={(j) => j.id}
            onRowClick={(j) => navigate(`/remediation/${j.id}`)}
            empty="No remediation jobs yet."
          />
          <Pagination
            total={query.data?.total ?? 0}
            limit={PAGE_SIZE}
            offset={offset}
            onChange={({ offset }) => setOffset(offset)}
          />
        </>
      )}
    </div>
  );
}
