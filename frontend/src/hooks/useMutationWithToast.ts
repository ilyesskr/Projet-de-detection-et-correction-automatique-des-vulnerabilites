import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/apiClient";

/**
 * Wraps `useMutation` so every write goes through the same toast UX:
 * a green success line on resolve, a red error line on reject. The
 * `errorMessage`/`successMessage` overrides accept either a static
 * string or a function of the result/error so per-call detail can
 * land in the toast (e.g., "Created user 'alice'").
 *
 * Form-level field errors (422) are NOT toasted — they belong on the
 * field via `react-hook-form.setError`. The 401 case is handled by
 * the apiClient interceptor and skipped here so the user doesn't see
 * both a "session expired" toast and a redundant mutation-failed one.
 */

interface MutationToastOptions<TData, TError, TVariables, TContext>
  extends UseMutationOptions<TData, TError, TVariables, TContext> {
  successMessage?: string | ((data: TData, variables: TVariables) => string);
  errorMessage?: string | ((error: TError, variables: TVariables) => string);
}

export function useMutationWithToast<
  TData = unknown,
  TError = ApiError,
  TVariables = void,
  TContext = unknown,
>(
  options: MutationToastOptions<TData, TError, TVariables, TContext>,
): UseMutationResult<TData, TError, TVariables, TContext> {
  const {
    successMessage,
    errorMessage,
    onSuccess,
    onError,
    ...rest
  } = options;

  return useMutation<TData, TError, TVariables, TContext>({
    ...rest,
    onSuccess: (data, variables, onMutateResult, context) => {
      if (successMessage) {
        const msg =
          typeof successMessage === "function"
            ? successMessage(data, variables)
            : successMessage;
        toast.success(msg);
      }
      onSuccess?.(data, variables, onMutateResult, context);
    },
    onError: (error, variables, onMutateResult, context) => {
      const apiError = error as unknown as ApiError;
      const isFieldErrorBody =
        apiError && apiError.status === 422 && !!apiError.fieldErrors;
      const isAuthExpired = apiError && apiError.status === 401;

      if (!isFieldErrorBody && !isAuthExpired) {
        const fallback =
          (apiError && apiError.detail) ||
          (error instanceof Error ? error.message : "Request failed");
        const msg =
          typeof errorMessage === "function"
            ? errorMessage(error, variables)
            : errorMessage ?? fallback;
        toast.error(msg);
      }
      onError?.(error, variables, onMutateResult, context);
    },
  });
}
