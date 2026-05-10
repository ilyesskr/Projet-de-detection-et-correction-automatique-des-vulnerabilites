import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (next: { limit: number; offset: number }) => void;
}

export function Pagination({ total, limit, offset, onChange }: PaginationProps) {
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  const goPrev = () => onChange({ limit, offset: Math.max(0, offset - limit) });
  const goNext = () =>
    onChange({ limit, offset: Math.min((pageCount - 1) * limit, offset + limit) });

  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground py-3">
      <div>
        {total === 0
          ? "No results"
          : `Showing ${from}–${to} of ${total}`}
      </div>
      <div className="flex items-center gap-2">
        <span className="hidden sm:inline">
          Page {page} of {pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={goPrev}
          disabled={offset === 0}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={goNext}
          disabled={page >= pageCount}
        >
          Next
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}
