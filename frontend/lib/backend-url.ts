/**
 * Central place to read the backend base URL.
 *
 * Trims whitespace and strips any trailing slash so that a value pasted
 * with a trailing "/" (e.g. "https://foo.onrender.com/") never produces a
 * double-slash when routes build paths like `${getBackendUrl()}/path`.
 */
export function getBackendUrl(): string {
  const raw = process.env.BACKEND_URL?.trim();
  if (!raw) return "http://localhost:8080";
  return raw.replace(/\/+$/, "");
}
