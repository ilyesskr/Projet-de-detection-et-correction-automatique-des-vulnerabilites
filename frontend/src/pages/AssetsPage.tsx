import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Pagination } from "@/components/data/Pagination";
import { ErrorState } from "@/components/feedback/ErrorState";
import { AssetStatusBadge } from "@/components/badges/AssetStatusBadge";

import { useAssets } from "@/hooks/queries/useAssets";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { dash, formatRelative } from "@/lib/format";
import type { Asset } from "@/api/types";

const PAGE_SIZE = 25;

export default function AssetsPage() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState("");
  const [offset, setOffset] = useState(0);

  const debouncedSearch = useDebouncedValue(searchInput, 300);

  const query = useAssets({
    limit: PAGE_SIZE,
    offset,
    search: debouncedSearch || undefined,
  });

  const columns: Column<Asset>[] = [
    {
      header: "Hostname",
      cell: (a) => (
        <span className="font-medium text-slate-100">
          {dash(a.hostname)}
        </span>
      ),
    },
    {
      header: "OS",
      cell: (a) => (
        <span className="text-slate-300">
          {a.os_name ? `${a.os_name} ${a.os_version ?? ""}`.trim() : "—"}
        </span>
      ),
    },
    { header: "Status",  cell: (a) => <AssetStatusBadge status={a.status} /> },
    { header: "IP",      cell: (a) => <span className="font-mono text-xs">{dash(a.ip_address)}</span> },
    { header: "Last seen", cell: (a) => formatRelative(a.last_seen) },
    { header: "Agent",   cell: (a) => <span className="font-mono text-xs">{dash(a.agent_version)}</span> },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Assets"
        description="Hosts synced from the Wazuh agent inventory."
      />

      <div className="mb-4 flex items-center gap-2">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              setOffset(0);
            }}
            placeholder="Search hostname…"
            className="pl-8"
          />
        </div>
      </div>

      {query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't load assets"
        />
      ) : (
        <>
          <DataTable<Asset>
            columns={columns}
            rows={query.data?.items}
            loading={query.isLoading}
            rowKey={(a) => a.id}
            onRowClick={(a) => navigate(`/assets/${a.id}`)}
            empty="No assets match your filters."
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
