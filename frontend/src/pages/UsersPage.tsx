import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Pagination } from "@/components/data/Pagination";
import { ErrorState } from "@/components/feedback/ErrorState";

import { useUsers } from "@/hooks/queries/useUsers";
import { UserDialog } from "@/components/users/UserDialog";
import { UserDetailDialog } from "@/components/users/UserDetailDialog";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import type { User } from "@/api/types";

const PAGE_SIZE = 25;

type ActiveFilter = "all" | "active" | "inactive";
const ACTIVE_LABEL: Record<ActiveFilter, string> = {
  all: "All",
  active: "Active only",
  inactive: "Inactive only",
};

export default function UsersPage() {
  const [filter, setFilter] = useState<ActiveFilter>("all");
  const [offset, setOffset] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<User | null>(null);

  const query = useUsers({
    limit: PAGE_SIZE,
    offset,
    is_active:
      filter === "all" ? undefined : filter === "active" ? true : false,
  });

  const columns: Column<User>[] = [
    {
      header: "Username",
      cell: (u) => (
        <span className="font-medium text-slate-100">{u.username}</span>
      ),
    },
    { header: "Email", cell: (u) => u.email },
    {
      header: "Status",
      cell: (u) => (
        <span className="inline-flex items-center gap-1.5 text-sm">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              u.is_active ? "bg-status-fixed" : "bg-status-failed",
            )}
            aria-hidden
          />
          {u.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      header: "Roles",
      cell: (u) =>
        u.roles.length === 0 ? (
          <span className="text-muted-foreground text-xs">—</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {u.roles.map((r) => (
              <span
                key={r.id}
                className="px-1.5 py-0.5 text-xs rounded border border-slate-700 bg-slate-800/60"
              >
                {r.name}
              </span>
            ))}
            {u.is_superuser && (
              <span className="px-1.5 py-0.5 text-xs rounded border border-status-approved/40 bg-status-approved/15 text-status-approved">
                superuser
              </span>
            )}
          </div>
        ),
    },
    { header: "Created", cell: (u) => formatDateTime(u.created_at) },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Users"
        description="Accounts that can sign in to the operator console."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New user
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="text-xs text-muted-foreground mr-1">Show:</span>
        {(Object.keys(ACTIVE_LABEL) as ActiveFilter[]).map((f) => {
          const selected = filter === f;
          return (
            <button
              key={f}
              type="button"
              onClick={() => {
                setFilter(f);
                setOffset(0);
              }}
              className={cn(
                "px-2 py-1 rounded-md text-xs border transition-colors",
                selected
                  ? "bg-slate-800 border-slate-600 text-slate-50"
                  : "border-slate-800 text-muted-foreground hover:text-slate-200",
              )}
            >
              {ACTIVE_LABEL[f]}
            </button>
          );
        })}
      </div>

      {query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't load users"
        />
      ) : (
        <>
          <DataTable<User>
            columns={columns}
            rows={query.data?.items}
            loading={query.isLoading}
            rowKey={(u) => u.id}
            onRowClick={(u) => setSelected(u)}
            empty="No users match this filter."
          />
          <Pagination
            total={query.data?.total ?? 0}
            limit={PAGE_SIZE}
            offset={offset}
            onChange={({ offset }) => setOffset(offset)}
          />
        </>
      )}

      <UserDialog open={createOpen} onOpenChange={setCreateOpen} />
      <UserDetailDialog
        user={selected}
        onOpenChange={(open) => !open && setSelected(null)}
      />
    </div>
  );
}
