import type { NextConfig } from "next";

// Backend URL resolution:
//   Local dev  — BACKEND_URL in .env.local  (default: http://localhost:8080)
//   Production — BACKEND_URL set in Vercel dashboard to the Render service URL
//
// The rewrite proxies /api/backend/* → <BACKEND_URL>/* server-side, so the
// actual backend host is never exposed in the browser bundle and no CORS
// configuration is needed on either side for frontend-initiated requests.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8080";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  compress: true,

  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },

  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion", "@xyflow/react"],
  },

  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 31536000,
  },

  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
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
