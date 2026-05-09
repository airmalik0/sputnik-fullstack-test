/**
 * Single source of truth for status -> Bootstrap-variant mapping.
 *
 * The original page rendered three near-identical badges with three
 * separate `getXxxVariant` switch functions. They all do the same job
 * (map a discriminated string to a colour) and consolidating them here
 * means a UX-wide colour change is a one-place edit.
 */

import { Badge } from "react-bootstrap";

type Variant = "success" | "warning" | "danger" | "secondary" | "info";

const PROCESSING_VARIANTS: Record<string, Variant> = {
  processed: "success",
  processing: "warning",
  failed: "danger",
  uploaded: "secondary",
};

const SCAN_VARIANTS: Record<string, Variant> = {
  clean: "success",
  suspicious: "warning",
  failed: "danger",
};

const ALERT_VARIANTS: Record<string, Variant> = {
  info: "success",
  warning: "warning",
  critical: "danger",
};

export function ProcessingBadge({ status }: { status: string }) {
  return <Badge bg={PROCESSING_VARIANTS[status] ?? "secondary"}>{status}</Badge>;
}

export function ScanBadge({ status, requiresAttention }: { status: string | null; requiresAttention: boolean }) {
  const label = status ?? "pending";
  const variant: Variant = status
    ? (SCAN_VARIANTS[status] ?? "secondary")
    : requiresAttention
      ? "warning"
      : "secondary";
  return <Badge bg={variant}>{label}</Badge>;
}

export function AlertLevelBadge({ level }: { level: string }) {
  return <Badge bg={ALERT_VARIANTS[level] ?? "secondary"}>{level}</Badge>;
}
