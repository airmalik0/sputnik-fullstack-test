"use client";

import { useCallback, useEffect, useState } from "react";

import { alertsApi } from "@/entities/alert/api";
import type { AlertItem } from "@/entities/alert/types";

type UseAlertsResult = {
  data: AlertItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
};

export function useAlerts(): UseAlertsResult {
  const [data, setData] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setData(await alertsApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить алерты");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}
