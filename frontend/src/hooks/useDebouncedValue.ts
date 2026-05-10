import { useEffect, useState } from "react";

/**
 * Tiny debounce hook for search inputs. Returns a value that lags
 * `delay` ms behind the source — TanStack Query keys built from this
 * value won't fan out a refetch on every keystroke.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);

  return debounced;
}
