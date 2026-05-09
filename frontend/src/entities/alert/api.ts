import { apiClient } from "@/shared/api/client";
import type { AlertItem } from "@/entities/alert/types";

export const alertsApi = {
  list: () => apiClient.get<AlertItem[]>("/alerts"),
};
