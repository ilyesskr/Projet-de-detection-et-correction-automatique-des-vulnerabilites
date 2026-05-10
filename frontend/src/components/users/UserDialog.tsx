import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

import { createUser, updateUser } from "@/api/users";
import type { ApiError } from "@/lib/apiClient";
import type { User } from "@/api/types";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { useRoles } from "@/hooks/queries/useUsers";

interface UserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Edit mode if `user` is provided; create mode otherwise. */
  user?: User;
}

/**
 * Create / edit user. Two modes:
 * - **Create:** username + password required (≥8), email required.
 * - **Edit:** username locked (server doesn't accept renames per
 *   `app/schemas/user.py::UserUpdate`); password optional.
 *
 * Roles are picked from `GET /roles`. We send `role_names` only when
 * the set has been touched, otherwise PATCH leaves the user's roles
 * unchanged.
 */
export function UserDialog({ open, onOpenChange, user }: UserDialogProps) {
  const isEdit = !!user;
  const queryClient = useQueryClient();
  const rolesQuery = useRoles();

  const baseSchema = z.object({
    username: z.string().min(1, "Username is required").max(64),
    email: z.string().email("Invalid email"),
    password: isEdit
      ? z.string().max(128).optional().or(z.literal(""))
      : z.string().min(8, "At least 8 characters").max(128),
    is_active: z.boolean(),
    is_superuser: z.boolean(),
    role_names: z.array(z.string()),
  });
  type FormValues = z.infer<typeof baseSchema>;

  const form = useForm<FormValues>({
    resolver: zodResolver(baseSchema),
    defaultValues: {
      username: user?.username ?? "",
      email: user?.email ?? "",
      password: "",
      is_active: user?.is_active ?? true,
      is_superuser: user?.is_superuser ?? false,
      role_names: user?.roles.map((r) => r.name) ?? [],
    },
  });

  // Re-seed defaults when the dialog reopens for a different user.
  useEffect(() => {
    if (!open) return;
    form.reset({
      username: user?.username ?? "",
      email: user?.email ?? "",
      password: "",
      is_active: user?.is_active ?? true,
      is_superuser: user?.is_superuser ?? false,
      role_names: user?.roles.map((r) => r.name) ?? [],
    });
  }, [open, user, form]);

  function applyServerErrors(error: ApiError) {
    if (error.status !== 422 || !error.fieldErrors) return;
    const fields: Array<keyof FormValues> = [
      "username",
      "email",
      "password",
      "is_active",
      "is_superuser",
      "role_names",
    ];
    for (const [field, msg] of Object.entries(error.fieldErrors)) {
      if (fields.includes(field as keyof FormValues)) {
        form.setError(field as keyof FormValues, { type: "server", message: msg });
      }
    }
  }

  const createMutation = useMutationWithToast<User, ApiError, FormValues>({
    mutationFn: (values) =>
      createUser({
        username: values.username,
        email: values.email,
        password: values.password!,
        is_active: values.is_active,
        is_superuser: values.is_superuser,
        role_names: values.role_names,
      }),
    successMessage: (u) => `Created user '${u.username}'`,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onOpenChange(false);
    },
    onError: applyServerErrors,
  });

  const updateMutation = useMutationWithToast<User, ApiError, FormValues>({
    mutationFn: (values) =>
      updateUser(user!.id, {
        email: values.email,
        password: values.password ? values.password : null,
        is_active: values.is_active,
        is_superuser: values.is_superuser,
        role_names: values.role_names,
      }),
    successMessage: (u) => `Updated user '${u.username}'`,
    onSuccess: (u) => {
      queryClient.setQueryData(["users", "detail", u.id], u);
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onOpenChange(false);
    },
    onError: applyServerErrors,
  });

  const submitting = createMutation.isPending || updateMutation.isPending;

  function onSubmit(values: FormValues) {
    if (isEdit) updateMutation.mutate(values);
    else createMutation.mutate(values);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? `Edit ${user.username}` : "Create user"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Username cannot be changed. Leave password blank to keep it."
              : "Pick a username, email, and initial password (≥8 characters)."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-4"
            noValidate
          >
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      autoComplete="off"
                      readOnly={isEdit}
                      className={isEdit ? "bg-muted/40" : ""}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input {...field} type="email" autoComplete="off" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {isEdit ? "New password (optional)" : "Password"}
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="password"
                      autoComplete="new-password"
                      placeholder={isEdit ? "Leave blank to keep current" : ""}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex flex-col gap-2">
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal cursor-pointer">
                      Active (can sign in)
                    </FormLabel>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="is_superuser"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal cursor-pointer">
                      Superuser (bypasses asset scope)
                    </FormLabel>
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="role_names"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Roles</FormLabel>
                  {rolesQuery.isLoading ? (
                    <Skeleton className="h-9" />
                  ) : (
                    <div className="flex flex-col gap-1.5 rounded-md border border-slate-800 p-3">
                      {(rolesQuery.data ?? []).map((r) => {
                        const checked = field.value.includes(r.name);
                        return (
                          <Label
                            key={r.id}
                            className="flex items-center gap-2 font-normal cursor-pointer"
                          >
                            <Checkbox
                              checked={checked}
                              onCheckedChange={(v) => {
                                const next = v
                                  ? [...field.value, r.name]
                                  : field.value.filter((n) => n !== r.name);
                                field.onChange(next);
                              }}
                            />
                            <span>{r.name}</span>
                            {r.description && (
                              <span className="text-xs text-muted-foreground truncate">
                                — {r.description}
                              </span>
                            )}
                          </Label>
                        );
                      })}
                    </div>
                  )}
                  <FormDescription>
                    Pick zero or more. Empty roles → user can sign in but
                    has no permissions.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => onOpenChange(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {isEdit ? "Save changes" : "Create user"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
