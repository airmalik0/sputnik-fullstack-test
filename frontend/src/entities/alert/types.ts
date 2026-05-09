/**
 * Alert entity — TS shape mirroring the API's AlertItem response.
 */

export type AlertItem = {
  id: number;
  file_id: string;
  level: "info" | "warning" | "critical";
  message: string;
  created_at: string;
};
