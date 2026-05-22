import { readCsrfCookie } from "./csrf";

export type ApiErrorBody = {
  error: string;
  detail?: unknown;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(`${status} ${body.error}`);
    this.status = status;
    this.code = body.error;
    this.detail = body.detail;
  }
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!SAFE_METHODS.has(method)) {
    const token = readCsrfCookie();
    if (token) headers.set("X-CSRF-Token", token);
  }

  const response = await fetch(path, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const body = text ? (JSON.parse(text) as unknown) : undefined;

  if (!response.ok) {
    throw new ApiError(response.status, (body as ApiErrorBody) ?? { error: "unknown" });
  }
  return body as T;
}
