/**
 * Tiny fetch wrapper.
 *
 * The original code repeated the same pattern at every call site:
 *   fetch(`${API}/path`, { cache: "no-store" })
 *     .then(r => r.ok ? r.json() : Promise.reject(...))
 *
 * Centralising this here yields three concrete wins:
 *
 *   - Error shape is consistent: every failed call rejects with a
 *     subclass of `ApiError` carrying the HTTP status, so callers can
 *     branch on 404 vs 500 without parsing strings.
 *   - The default of `cache: "no-store"` is enforced, which matters
 *     because Next's built-in fetch cache otherwise serves stale data
 *     after a successful upload.
 *   - Adding cross-cutting concerns later (auth header, request id,
 *     telemetry) means editing one file, not five.
 */

import { API_URL } from "@/shared/config";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestInitJSON = Omit<RequestInit, "body"> & {
  body?: BodyInit | null | unknown;
  json?: unknown;
};

async function request<T>(path: string, init: RequestInitJSON = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const finalHeaders = new Headers(headers as HeadersInit | undefined);
  let body: BodyInit | null | undefined = init.body as BodyInit | null | undefined;

  if (json !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  } else if (!isFormData && body !== undefined && body !== null && typeof body === "object") {
    // Belt-and-braces: callers should use `json:` rather than passing an
    // object as `body`, but be forgiving.
    finalHeaders.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...rest,
    headers: finalHeaders,
    body: body as BodyInit | null | undefined,
  });

  if (!response.ok) {
    // Try to surface the FastAPI `{detail: ...}` envelope so the UI can
    // show something more useful than "request failed". Falls back to a
    // generic message if the body isn't JSON or doesn't have `detail`.
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data && typeof data === "object" && "detail" in data) {
        detail = String((data as { detail: unknown }).detail);
      }
    } catch {
      // Non-JSON response body — keep the status fallback.
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string, init?: RequestInitJSON) =>
    request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, init?: RequestInitJSON) =>
    request<T>(path, { ...init, method: "POST" }),
  patch: <T>(path: string, init?: RequestInitJSON) =>
    request<T>(path, { ...init, method: "PATCH" }),
  delete: <T>(path: string, init?: RequestInitJSON) =>
    request<T>(path, { ...init, method: "DELETE" }),
};
