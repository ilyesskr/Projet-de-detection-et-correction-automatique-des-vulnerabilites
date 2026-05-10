import { LogOut, ShieldCheck, UserCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/stores/auth";
import { useLogout } from "@/hooks/useLogout";

/**
 * Top-right identity menu. Shows username + primary role; "Sign out"
 * uses `useLogout` (no server-side revocation yet — backend feature
 * (b) is deferred). When the store has no user (e.g., bootstrap is
 * still running), the trigger is hidden rather than rendering an
 * empty pill that flashes on first paint.
 */
export default function UserMenu() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();

  if (!user) return null;

  const initials = (user.username || "?").slice(0, 2).toUpperCase();
  // Pick the first assigned role as the "primary" — we don't have a
  // notion of a primary role on the backend yet; sorted alphabetically
  // means "admin" wins over "viewer" which is the right default UX.
  const primaryRole =
    [...user.roles].sort((a, b) => a.name.localeCompare(b.name))[0]?.name;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="h-9 gap-2 px-2 text-slate-200 hover:text-slate-50"
        >
          <span
            className="h-7 w-7 rounded-full bg-slate-700 text-slate-100 text-xs font-semibold flex items-center justify-center"
            aria-hidden
          >
            {initials}
          </span>
          <span className="hidden sm:inline text-sm font-medium">
            {user.username}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="text-sm font-medium">{user.username}</span>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            {user.is_superuser ? (
              <>
                <ShieldCheck className="h-3 w-3" /> Superuser
              </>
            ) : primaryRole ? (
              <>
                <UserCircle2 className="h-3 w-3" /> {primaryRole}
              </>
            ) : (
              "No role"
            )}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout}>
          <LogOut className="h-4 w-4 mr-2" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
