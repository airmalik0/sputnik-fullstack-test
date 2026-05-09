/**
 * Files data-fetching hook.
 *
 * Manual implementation in this commit (matches the original
 * useEffect+useState shape, just relocated). Replaced by react-query
 * with adaptive polling in the next commit; the hook signature is
 * stable so the page does not change shape.
 */

"use client";

import { useCallback, useEffect, useState } from "react";

import { filesApi } from "@/entities/file/api";
import type { FileItem } from "@/entities/file/types";

type UseFilesResult = {
  data: FileItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
};

export function useFiles(): UseFilesResult {
  const [data, setData] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setData(await filesApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить файлы");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}
