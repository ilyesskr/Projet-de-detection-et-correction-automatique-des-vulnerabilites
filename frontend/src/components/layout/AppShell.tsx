import { useState } from "react";
import { Outlet } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";

import SideNav from "@/components/layout/SideNav";
import UserMenu from "@/components/layout/UserMenu";

/**
 * Three-region layout: sidebar | top bar | content.
 *
 * Mobile is explicitly out of scope for the first version (build plan
 * Phase 3) — the sidebar collapses to an icon rail on tablet width and
 * stays present on phones rather than turning into a sheet. A header
 * toggle button lets the user collapse/expand on demand.
 *
 * Wraps in a single TooltipProvider so the collapsed-rail nav tooltips
 * can render without each item declaring its own provider.
 */
export default function AppShell() {
  // Default expanded on lg+; the user can collapse to recover horizontal
  // space on smaller screens. Persisting the preference is a Phase 6+
  // concern — not worth localStorage plumbing yet.
  const [expanded, setExpanded] = useState<boolean>(
    typeof window !== "undefined" ? window.innerWidth >= 1024 : true,
  );

  return (
    <TooltipProvider delayDuration={300}>
      <div className="min-h-screen flex bg-slate-900 text-slate-100">
        <SideNav expanded={expanded} />

        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-14 flex items-center justify-between border-b border-slate-800 bg-slate-950/60 backdrop-blur px-3">
            <Button
              variant="ghost"
              size="icon"
              className="text-slate-300 hover:text-slate-50"
              onClick={() => setExpanded((v) => !v)}
              aria-label={
                expanded ? "Collapse sidebar" : "Expand sidebar"
              }
            >
              {expanded ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeftOpen className="h-4 w-4" />
              )}
            </Button>

            <UserMenu />
          </header>

          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
