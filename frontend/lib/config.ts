/**
 * Central frontend configuration.
 *
 * All backend calls go through the Next.js rewrite at /api/backend/* —
 * next.config.ts proxies that to the real backend URL (BACKEND_URL env var,
 * server-side only). Client code never needs to know the actual host.
 *
 * Environment detection:
 *   Local dev  — VERCEL is unset; BACKEND_URL defaults to localhost:8080
 *   Vercel     — VERCEL="1"; BACKEND_URL must be set in the Vercel dashboard
 *                to the Render service URL (e.g. https://your-app.onrender.com)
 */

/** Prefix for all backend API calls. Proxied by Next.js to BACKEND_URL. */
export const BACKEND_PATH = "/api/backend";

/**
 * Current deployment environment label.
 * Available on the server; NEXT_PUBLIC_VERCEL_ENV is available in the browser.
 */
export const ENVIRONMENT: string =
  process.env.NEXT_PUBLIC_VERCEL_ENV ?? "local";

/** True when running on Vercel (any environment — production, preview, dev). */
export const IS_VERCEL = ENVIRONMENT !== "local";
