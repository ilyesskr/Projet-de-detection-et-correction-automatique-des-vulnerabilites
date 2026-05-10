import {
  ClipboardList,
  LayoutDashboard,
  PlugZap,
  ServerCog,
  ShieldAlert,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";

/**
 * Single source of truth for the operator-console navigation.
 *
 * `permission` is matched against the auth store's resolved permission
 * set. `undefined` means "any authenticated user" (the dashboard is the
 * only such item — see spec §6 / §9). The SideNav filters by
 * `usePermissions().has(item.permission)`.
 *
 * Keep ordered top-to-bottom in the order the nav should render.
 */

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  /** Permission string from `app/core/permissions.py`. */
  permission?: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { label: "Dashboard",       path: "/",               icon: LayoutDashboard },
  { label: "Assets",          path: "/assets",         icon: ServerCog,    permission: "assets:read" },
  { label: "Vulnerabilities", path: "/vulnerabilities", icon: ShieldAlert, permission: "vulnerabilities:read" },
  { label: "Remediation",     path: "/remediation",    icon: Wrench,       permission: "remediation:read" },
  { label: "Users",           path: "/users",          icon: Users,        permission: "users:manage" },
  { label: "Audit",           path: "/audit",          icon: ClipboardList, permission: "audit:read" },
  { label: "Integrations",    path: "/integrations",   icon: PlugZap,      permission: "integrations:read" },
];
