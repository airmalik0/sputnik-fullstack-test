/**
 * Files data hook backed by react-query, with adaptive polling.
 *
 * The interesting bit is `refetchInterval`: while at least one file is
 * in a non-terminal processing state (uploaded / processing), we poll
 * every 2 seconds so the user sees status transitions live. The instant
 * every file reaches a terminal state, polling stops on its own. The
 * original page required clicking "Обновить" to see scan results; this
 * makes it automatic without burning network when nothing is happening.
 */

"use client";

import { useQuery } from "@tanstack/react-query";

import { filesApi } from "@/entities/file/api";
import { TERMINAL_PROCESSING_STATES, type FileItem } from "@/entities/file/types";

export const FILES_QUERY_KEY = ["files"] as const;

const POLL_INTERVAL_MS = 2_000;

export function useFiles() {
  return useQuery<FileItem[]>({
    queryKey: FILES_QUERY_KEY,
    queryFn: () => filesApi.list(),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.length === 0) return false;
      const stillWorking = data.some(
        (file) => !TERMINAL_PROCESSING_STATES.includes(file.processing_status),
      );
      return stillWorking ? POLL_INTERVAL_MS : false;
    },
  });
}
