"use client";

import { useQuery } from "@tanstack/react-query";

import { alertsApi } from "@/entities/alert/api";
import type { AlertItem } from "@/entities/alert/types";

export const ALERTS_QUERY_KEY = ["alerts"] as const;

export function useAlerts() {
  return useQuery<AlertItem[]>({
    queryKey: ALERTS_QUERY_KEY,
    queryFn: () => alertsApi.list(),
    // Alerts are written by the same task that updates file status, so
    // we don't need separate polling — invalidating on the files
    // refetch keeps both views in sync. See useFiles for the refresh
    // cadence; the consumer wires up cross-invalidation in the upload
    // mutation.
  });
}
