/**
 * Display formatters used by every read page.
 *
 * All functions accept `null | undefined` and return a fallback rather
 * than throwing — list rows from the backend often have nullable
 * columns (last_seen, ip_address, etc.) and we'd rather render `—`
 * than crash a row.
 */

export const EMPTY = "—";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;
  return d.toLocaleString();
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;
  return d.toLocaleDateString();
}

/**
 * "5 min ago" / "in 2 days". Uses Intl.RelativeTimeFormat so the unit
 * matches the user's locale. Falls back to absolute date for spans
 * older than 30 days where "23 days ago" is less useful than the
 * actual date.
 */
export function formatRelative(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;

  const diffMs = d.getTime() - Date.now();
  const diffSec = Math.round(diffMs / 1000);
  const absSec = Math.abs(diffSec);

  if (absSec > 30 * 24 * 3600) return d.toLocaleDateString();

  const fmt = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (absSec < 60) return fmt.format(diffSec, "second");
  if (absSec < 3600) return fmt.format(Math.round(diffSec / 60), "minute");
  if (absSec < 86_400) return fmt.format(Math.round(diffSec / 3600), "hour");
  return fmt.format(Math.round(diffSec / 86_400), "day");
}

/** Render a cell value, replacing null/undefined/"" with `—`. */
export function dash<T>(value: T | null | undefined): T | string {
  if (value === null || value === undefined || value === "") return EMPTY;
  return value;
}
