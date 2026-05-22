/**
 * Read the `csrf_token` cookie that the backend sets via after_request.
 * Returns null if the cookie hasn't been seeded yet (e.g. very first
 * request before any response has come back).
 */
export function readCsrfCookie(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}
