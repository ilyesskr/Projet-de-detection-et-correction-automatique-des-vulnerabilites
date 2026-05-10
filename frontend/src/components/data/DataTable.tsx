import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

export interface Column<T> {
  /** Header text. */
  header: ReactNode;
  /** Cell renderer. */
  cell: (row: T) => ReactNode;
  /** Optional Tailwind classes for the cell + header (alignment, width). */
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  loading?: boolean;
  /** Stable id for the row, used as key + click target. */
  rowKey: (row: T) => string;
  /** Triggered when a row is clicked or activated by keyboard. */
  onRowClick?: (row: T) => void;
  /**
   * What to render when rows is `[]`. Pass an `<EmptyState />` for the
   * usual "no results" message; pass plain text for one-off cases.
   */
  empty?: ReactNode;
  /** Number of skeleton rows to render while `loading`. */
  skeletonRows?: number;
}

/**
 * Generic table backed by shadcn primitives. Intentionally NOT
 * column-resizable / sortable / virtualized — for the operator console
 * none of the tables exceed a few thousand rows server-side, and
 * pagination is the source of truth for size.
 */
export function DataTable<T>({
  columns,
  rows,
  loading,
  rowKey,
  onRowClick,
  empty,
  skeletonRows = 6,
}: DataTableProps<T>) {
  return (
    <div className="rounded-md border border-slate-800 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {columns.map((col, i) => (
              <TableHead key={i} className={col.className}>
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading
            ? Array.from({ length: skeletonRows }).map((_, i) => (
                <TableRow key={`sk-${i}`} className="hover:bg-transparent">
                  {columns.map((_col, j) => (
                    <TableCell key={j} className={_col.className}>
                      <Skeleton className="h-4 w-3/4" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : rows && rows.length > 0
              ? rows.map((row) => {
                  const handleClick = onRowClick
                    ? () => onRowClick(row)
                    : undefined;
                  return (
                    <TableRow
                      key={rowKey(row)}
                      className={cn(onRowClick && "cursor-pointer")}
                      onClick={handleClick}
                      tabIndex={onRowClick ? 0 : undefined}
                      onKeyDown={
                        onRowClick
                          ? (e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                onRowClick(row);
                              }
                            }
                          : undefined
                      }
                    >
                      {columns.map((col, i) => (
                        <TableCell key={i} className={col.className}>
                          {col.cell(row)}
                        </TableCell>
                      ))}
                    </TableRow>
                  );
                })
              : (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={columns.length}
                    className="h-32 text-center text-sm text-muted-foreground"
                  >
                    {empty ?? "No results."}
                  </TableCell>
                </TableRow>
              )}
        </TableBody>
      </Table>
    </div>
  );
}
