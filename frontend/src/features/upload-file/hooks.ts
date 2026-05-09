/**
 * Upload mutation.
 *
 * On success, invalidates both the files and alerts queries so the
 * tables refresh together — the new file shows up in the files list
 * and (once the worker finishes) the corresponding alert lands in the
 * alerts feed via the polling cycle.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ALERTS_QUERY_KEY } from "@/entities/alert/hooks";
import { filesApi } from "@/entities/file/api";
import { FILES_QUERY_KEY } from "@/entities/file/hooks";
import type { FileItem } from "@/entities/file/types";

export function useUploadFile() {
  const client = useQueryClient();
  return useMutation<FileItem, Error, FormData>({
    mutationFn: (form: FormData) => filesApi.upload(form),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: FILES_QUERY_KEY });
      void client.invalidateQueries({ queryKey: ALERTS_QUERY_KEY });
    },
  });
}
