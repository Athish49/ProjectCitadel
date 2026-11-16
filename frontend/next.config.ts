import type { NextConfig } from "next";

// Backend URL resolution:
//   Local dev  — BACKEND_URL in .env.local  (default: http://localhost:8080)
//   Production — BACKEND_URL set in Vercel dashboard to the Render service URL
//
// Each app/api/** route handler proxies its own request to BACKEND_URL
// server-side (see app/api/showcase/playground/route.ts etc.), so the actual
// backend host is never exposed in the browser bundle and no CORS
// configuration is needed on either side for frontend-initiated requests.

const nextConfig: NextConfig = {
  poweredByHeader: false,
  compress: true,

  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 31536000,
  },

  async headers() {
    // The 1-year immutable cache is only safe once /_next/static/* filenames
    // are truly content-hashed, which is a production-build guarantee.
    // Turbopack's dev-mode chunk filenames are NOT stable across restarts in
    // the same way, so applying this in dev makes the browser serve stale
    // JS/CSS after every `next dev` restart until a hard cache-clear —
    // restrict it to production.
    const staticCacheHeaders =
      process.env.NODE_ENV === "production"
        ? [
            {
              source: "/_next/static/:path*",
              headers: [
                {
                  key: "Cache-Control",
                  value: "public, max-age=31536000, immutable",
                },
              ],
            },
          ]
        : [];

    return [
      ...staticCacheHeaders,
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
