/**
 * File entity — the canonical TS shape mirroring the API's FileItem
 * response. Kept as a plain type (no class, no constructor) because
 * nothing in the frontend mutates a server-owned object: we read,
 * render, and discard.
 */

export type FileItem = {
  id: string;
  title: string;
  original_name: string;
  mime_type: string;
  size: number;
  processing_status: "uploaded" | "processing" | "processed" | "failed";
  scan_status: "clean" | "suspicious" | "failed" | null;
  scan_details: string | null;
  metadata_json: Record<string, unknown> | null;
  requires_attention: boolean;
  created_at: string;
  updated_at: string;
};

/**
 * The terminal states for processing. Used by polling logic to decide
 * when to stop refetching (anything else means a Celery task is still
 * working and the user benefits from automatic refresh).
 */
export const TERMINAL_PROCESSING_STATES: ReadonlyArray<FileItem["processing_status"]> = [
  "processed",
  "failed",
];
