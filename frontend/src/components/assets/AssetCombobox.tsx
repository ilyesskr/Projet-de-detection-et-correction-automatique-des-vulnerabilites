import { useState } from "react";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

import { useAssets } from "@/hooks/queries/useAssets";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { cn } from "@/lib/utils";
import type { Asset } from "@/api/types";

interface AssetComboboxProps {
  /** Selected asset id (controlled). */
  value?: string;
  /** Called when an option is picked. */
  onChange: (asset: Asset) => void;
  placeholder?: string;
  disabled?: boolean;
  /** Asset ids to hide from the suggestions (e.g., already-scoped). */
  excludeIds?: ReadonlySet<string>;
}

/**
 * Asset picker backed by `GET /assets?search=`.
 *
 * Server-side search rather than client-side filtering — the asset
 * inventory can be thousands of agents, so loading them all up front
 * would be wasteful. cmdk's built-in filtering is disabled
 * (`shouldFilter={false}`) so the input goes straight to the backend
 * via `useAssets`.
 */
export function AssetCombobox({
  value,
  onChange,
  placeholder = "Pick an asset…",
  disabled,
  excludeIds,
}: AssetComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useAssets({
    limit: 25,
    offset: 0,
    search: debouncedSearch || undefined,
  });

  const items = (query.data?.items ?? []).filter(
    (a) => !excludeIds?.has(a.id),
  );

  const selected = items.find((a) => a.id === value);
  const triggerLabel = selected
    ? selected.hostname || selected.wazuh_agent_id
    : placeholder;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between font-normal"
        >
          <span className={cn(!selected && "text-muted-foreground")}>
            {triggerLabel}
          </span>
          <ChevronsUpDown className="h-4 w-4 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-[--radix-popover-trigger-width]" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            value={search}
            onValueChange={setSearch}
            placeholder="Search hostname…"
          />
          <CommandList>
            {query.isLoading ? (
              <div className="py-6 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching…
              </div>
            ) : items.length === 0 ? (
              <CommandEmpty>No assets match.</CommandEmpty>
            ) : (
              <CommandGroup>
                {items.map((a) => (
                  <CommandItem
                    key={a.id}
                    value={a.id}
                    onSelect={() => {
                      onChange(a);
                      setOpen(false);
                      setSearch("");
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === a.id ? "opacity-100" : "opacity-0",
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm">
                        {a.hostname || a.wazuh_agent_id}
                      </div>
                      <div className="truncate text-xs text-muted-foreground font-mono">
                        {a.wazuh_agent_id}
                        {a.ip_address ? ` · ${a.ip_address}` : ""}
                      </div>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
