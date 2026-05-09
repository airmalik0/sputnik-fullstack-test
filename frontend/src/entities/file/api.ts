/**
 * File HTTP endpoints.
 *
 * One module per entity keeps the URL structure local — if the
 * backend rewrites `/files` to `/api/v1/files`, only this file changes.
 * Components import `filesApi.list()` and stay decoupled from URL
 * shape and HTTP verbs.
 */

import { apiClient } from "@/shared/api/client";
import { API_URL } from "@/shared/config";
import type { FileItem } from "@/entities/file/types";

export const filesApi = {
  list: () => apiClient.get<FileItem[]>("/files"),

  upload: (form: FormData) => apiClient.post<FileItem>("/files", { body: form }),

  remove: (id: string) => apiClient.delete<void>(`/files/${id}`),

  /**
   * Download URL is constructed (not fetched) because the browser
   * navigates to it directly via an <a> tag — going through fetch
   * would buffer the file in JS memory just to hand it back to the
   * browser to save.
   */
  downloadUrl: (id: string) => `${API_URL}/files/${id}/download`,
};
