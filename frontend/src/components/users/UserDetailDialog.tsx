import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

import { AssetScopeSection } from "@/components/users/AssetScopeSection";
import { UserDialog } from "@/components/users/UserDialog";
import { deleteUser } from "@/api/users";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { User } from "@/api/types";

interface UserDetailDialogProps {
  user: User | null;
  onOpenChange: (open: boolean) => void;
}

/**
 * Detail panel for an existing user. Two tabs:
 * - **Profile** — read-only summary plus an "Edit" button that opens
 *   the create/edit dialog in edit mode.
 * - **Asset scope** — list/grant/revoke. Shows superuser banner when
 *   `is_superuser=true`.
 *
 * Delete lives at the bottom of the Profile tab and uses an
 * `<input type="text">` confirmation pattern (shadcn doesn't ship a
 * destructive-confirm component) so an admin cannot click-through it
 * by accident.
 */
export function UserDetailDialog({ user, onOpenChange }: UserDetailDialogProps) {
  const open = !!user;
  const [editOpen, setEditOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const queryClient = useQueryClient();

  const deleteMutation = useMutationWithToast({
    mutationFn: () => deleteUser(user!.id),
    successMessage: () => `Deleted user '${user!.username}'`,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onOpenChange(false);
    },
  });

  if (!user) return null;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{user.username}</DialogTitle>
            <DialogDescription className="flex items-center gap-1.5">
              <span
                className={cn(
                  "inline-block h-1.5 w-1.5 rounded-full",
                  user.is_active ? "bg-status-fixed" : "bg-status-failed",
                )}
                aria-hidden
              />
              {user.is_active ? "Active" : "Inactive"}
              {user.is_superuser && " · Superuser"}
              {" · "}
              {user.email}
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="profile">
            <TabsList className="w-full">
              <TabsTrigger value="profile" className="flex-1">
                Profile
              </TabsTrigger>
              <TabsTrigger value="scope" className="flex-1">
                Asset scope
              </TabsTrigger>
            </TabsList>

            <TabsContent value="profile" className="space-y-4 mt-4">
              <div className="text-sm space-y-1.5">
                <DetailRow label="User id" value={user.id} mono />
                <DetailRow
                  label="Roles"
                  value={
                    user.roles.length > 0 ? (
                      <span className="flex flex-wrap gap-1 justify-end">
                        {user.roles.map((r) => (
                          <span
                            key={r.id}
                            className="px-1.5 py-0.5 text-xs rounded border border-slate-700 bg-slate-800/60"
                          >
                            {r.name}
                          </span>
                        ))}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">none</span>
                    )
                  }
                />
                <DetailRow label="Created"  value={formatDateTime(user.created_at)} />
                <DetailRow label="Updated"  value={formatDateTime(user.updated_at)} />
              </div>

              <Separator />

              <div>
                <h3 className="text-sm font-medium mb-2 text-destructive">
                  Danger zone
                </h3>
                <p className="text-xs text-muted-foreground mb-2">
                  Type <span className="font-mono">{user.username}</span> to
                  confirm deletion. The audit trail is preserved.
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    placeholder={user.username}
                    className="flex-1 h-9 rounded-md border border-slate-800 bg-transparent px-3 text-sm font-mono"
                  />
                  <Button
                    variant="destructive"
                    onClick={() => deleteMutation.mutate()}
                    disabled={
                      confirm !== user.username || deleteMutation.isPending
                    }
                  >
                    {deleteMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4 mr-2" />
                    )}
                    Delete
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="scope" className="mt-4">
              <AssetScopeSection user={user} />
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button onClick={() => onOpenChange(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <UserDialog open={editOpen} onOpenChange={setEditOpen} user={user} />
    </>
  );
}

interface DetailRowProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}
function DetailRow({ label, value, mono }: DetailRowProps) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-xs text-right" : "text-right"}>
        {value}
      </span>
    </div>
  );
}
