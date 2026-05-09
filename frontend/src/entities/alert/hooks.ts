/**
 * Alerts data hook with adaptive polling.
 *
 * Alerts are written as a side effect of the same Celery task that
 * advances `processing_status` on a file. It would be wasteful to poll
 * alerts at a fixed cadence — we only need fresh alerts while the
 * worker is actually doing work. We read the files cache directly to
 * decide that.
 *
 * The cross-entity dependency (alert hook touching files types and the
 * files query key) is intentional: alerts are dependent on file
 * processing in the domain model, and pretending otherwise would mean
 * either constant polling or a manual refresh button — both of which
 * we already established are worse UX.
 */

"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { alertsApi } from "@/entities/alert/api";
import type { AlertItem } from "@/entities/alert/types";
import { FILES_QUERY_KEY } from "@/entities/file/hooks";
import { TERMINAL_PROCESSING_STATES, type FileItem } from "@/entities/file/types";

export const ALERTS_QUERY_KEY = ["alerts"] as const;

const POLL_INTERVAL_MS = 2_000;

export function useAlerts() {
  const queryClient = useQueryClient();

  return useQuery<AlertItem[]>({
    queryKey: ALERTS_QUERY_KEY,
    queryFn: () => alertsApi.list(),
    refetchInterval: () => {
      const files = queryClient.getQueryData<FileItem[]>(FILES_QUERY_KEY);
      if (!files || files.length === 0) return false;
      const stillWorking = files.some(
        (file) => !TERMINAL_PROCESSING_STATES.includes(file.processing_status),
      );
      return stillWorking ? POLL_INTERVAL_MS : false;
    },
  });
}
