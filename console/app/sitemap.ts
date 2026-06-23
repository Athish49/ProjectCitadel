import type { MetadataRoute } from "next";

const BASE = "https://secureclaim.example";

const STATIC_ROUTES = [
  "/",
  "/playground",
  "/architecture",
  "/matrix",
  "/patterns",
  "/adversary",
  "/audit",
  "/demo",
  "/formal",
  "/residual",
  "/api",
  "/docs",
  "/about",
] as const;

const PATTERN_IDS = ["p1","p2","p3","p4","p5","p6","p7","p8","p9","p10","p11","p12"] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map((route) => ({
    url: `${BASE}${route}`,
    lastModified: now,
    changeFrequency: route === "/" ? "daily" : "weekly",
    priority: route === "/" ? 1 : route === "/playground" ? 0.9 : 0.8,
  }));

  const patternEntries: MetadataRoute.Sitemap = PATTERN_IDS.map((id) => ({
    url: `${BASE}/patterns/${id}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  return [...staticEntries, ...patternEntries];
}
