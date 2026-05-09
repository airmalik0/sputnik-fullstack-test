/**
 * Formatting helpers used across multiple feature surfaces.
 *
 * Lifted out of `page.tsx` so the same date/size formatting is reused
 * everywhere — e.g. in the upcoming alerts feed and a future file
 * detail view — without copy-pasting Intl boilerplate.
 */

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
