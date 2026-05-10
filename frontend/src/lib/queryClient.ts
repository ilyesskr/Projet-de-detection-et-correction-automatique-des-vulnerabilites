import { QueryClient } from "@tanstack/react-query";

/**
 * One QueryClient instance for the whole app.
 *
 * Defaults are tuned for an operator console where stale data is
 * cheaper than thundering-herd refetches:
 * - 30 s `staleTime` so casual tab-switching doesn't refetch.
 * - No retries on 4xx (no point retrying a 403). Retry once on 5xx /
 *   network errors so transient backend hiccups don't break the page.
 * - `refetchOnWindowFocus` left on (default) so coming back to the tab
 *   gets fresh status counts on the dashboard.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        const status = (error as { status?: number } | null)?.status;
        if (status && status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
