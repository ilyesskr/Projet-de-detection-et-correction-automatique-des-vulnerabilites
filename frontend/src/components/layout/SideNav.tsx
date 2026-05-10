import { NavLink, useLocation } from "react-router-dom";
import { ShieldCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { usePermissions } from "@/hooks/usePermissions";
import { NAV_ITEMS } from "@/components/layout/navItems";

interface SideNavProps {
  /**
   * `false` = icon-rail (collapsed); `true` = full width with labels.
   * The shell controls this via a top-bar toggle button.
   */
  expanded: boolean;
}

export default function SideNav({ expanded }: SideNavProps) {
  const { has } = usePermissions();
  const location = useLocation();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.permission || has(item.permission),
  );

  return (
    <aside
      className={cn(
        "h-full bg-slate-950 border-r border-slate-800 flex flex-col",
        "transition-[width] duration-150 ease-out",
        expanded ? "w-56" : "w-14",
      )}
      aria-label="Primary navigation"
    >
      <div
        className={cn(
          "h-14 flex items-center gap-2.5 border-b border-slate-800",
          expanded ? "px-3" : "justify-center px-0",
        )}
      >
        <span className="relative flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 shadow-md shadow-blue-500/20 shrink-0">
          <ShieldCheck className="h-4 w-4 text-slate-950" />
        </span>
        {expanded && (
          <div className="leading-tight min-w-0">
            <div className="font-semibold tracking-tight text-slate-100 text-sm">
              PA Platform
            </div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Operator console
            </div>
          </div>
        )}
      </div>

      <nav className="flex-1 py-3">
        <ul className="space-y-1 px-2">
          {visibleItems.map((item) => {
            // Active rule: exact match on `/`; prefix match for everything
            // else so `/assets/abc` highlights "Assets". Tracking active
            // here instead of via NavLink's built-in lets us share the
            // same logic with the collapsed-tooltip variant.
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname === item.path ||
                  location.pathname.startsWith(item.path + "/");

            const Icon = item.icon;
            const link = (
              <NavLink
                to={item.path}
                className={cn(
                  "flex items-center rounded-md text-sm transition-colors",
                  expanded ? "h-9 px-3 gap-3" : "h-9 w-9 justify-center mx-auto",
                  isActive
                    ? "bg-slate-800 text-slate-50"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60",
                )}
                end={item.path === "/"}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {expanded && <span className="truncate">{item.label}</span>}
              </NavLink>
            );

            return (
              <li key={item.path}>
                {expanded ? (
                  link
                ) : (
                  <Tooltip>
                    <TooltipTrigger asChild>{link}</TooltipTrigger>
                    <TooltipContent side="right">{item.label}</TooltipContent>
                  </Tooltip>
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
