import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { z } from "zod";

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
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { createRemediationJob } from "@/api/remediation";
import {
  REMEDIATION_ACTIONS,
  type RemediationAction,
  type RemediationJob,
} from "@/api/types";
import type { ApiError } from "@/lib/apiClient";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";

const ACTION_LABEL: Record<RemediationAction, string> = {
  package_update: "Package update",
  windows_update: "Windows update",
  service_restart: "Service restart",
  config_change: "Config change",
};

const schema = z.object({
  asset_id: z.string().min(1, "Asset is required"),
  vulnerability_id: z.string().optional(),
  action: z.enum(REMEDIATION_ACTIONS),
  note: z.string().max(2000).optional(),
});
type FormValues = z.infer<typeof schema>;

interface CreateJobDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-filled and locked when set (asset detail / vuln-row launch). */
  assetId: string;
  /** Pre-filled and locked when set (vuln-row launch). */
  vulnerabilityId?: string;
  /** Optional context line for the dialog header (e.g., CVE-2024-…). */
  contextLabel?: string;
}

/**
 * Create a remediation job. Asset is always preselected; the field is
 * shown read-only so the user sees what they're acting on. Vulnerability
 * is optional — if launched from a vuln row it's preselected and locked,
 * otherwise it's omitted.
 *
 * `created_by` is derived server-side from the JWT (spec §8.7), so the
 * frontend never sends it.
 */
export function CreateJobDialog({
  open,
  onOpenChange,
  assetId,
  vulnerabilityId,
  contextLabel,
}: CreateJobDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      asset_id: assetId,
      vulnerability_id: vulnerabilityId,
      action: "package_update",
      note: "",
    },
  });

  // Re-sync defaults when the dialog reopens with different context
  // (e.g., the user clicks a different vuln row).
  useEffect(() => {
    if (open) {
      form.reset({
        asset_id: assetId,
        vulnerability_id: vulnerabilityId,
        action: "package_update",
        note: "",
      });
    }
  }, [open, assetId, vulnerabilityId, form]);

  const createMutation = useMutationWithToast<
    RemediationJob,
    ApiError,
    FormValues
  >({
    mutationFn: (values) =>
      createRemediationJob({
        asset_id: values.asset_id,
        vulnerability_id: values.vulnerability_id || null,
        action: values.action,
        note: values.note?.trim() || null,
      }),
    successMessage: "Remediation job created",
    onSuccess: (job) => {
      // Refresh any list that might now include this job. Detail-route
      // navigation will fetch the new job's record fresh.
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
      onOpenChange(false);
      navigate(`/remediation/${job.id}`);
    },
    onError: (error) => {
      // 422 → field errors back onto the form so the user can correct.
      if (error.status === 422 && error.fieldErrors) {
        for (const [field, msg] of Object.entries(error.fieldErrors)) {
          if (field === "asset_id" || field === "action" || field === "note") {
            form.setError(field as keyof FormValues, {
              type: "server",
              message: msg,
            });
          }
        }
      }
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create remediation job</DialogTitle>
          <DialogDescription>
            {contextLabel
              ? `Target: ${contextLabel}`
              : "Pick a remediation action for this asset."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}
            className="space-y-4"
            noValidate
          >
            <FormField
              control={form.control}
              name="asset_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Asset</FormLabel>
                  <FormControl>
                    <Input {...field} readOnly className="font-mono text-xs" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {vulnerabilityId && (
              <FormField
                control={form.control}
                name="vulnerability_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vulnerability</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        value={field.value ?? ""}
                        readOnly
                        className="font-mono text-xs"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control}
              name="action"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Action</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {REMEDIATION_ACTIONS.map((a) => (
                        <SelectItem key={a} value={a}>
                          {ACTION_LABEL[a]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Note (optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder="Why is this remediation needed?"
                      rows={3}
                    />
                  </FormControl>
                  <FormDescription>
                    Stored on the job record and the audit trail.
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
                disabled={createMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Create job
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
