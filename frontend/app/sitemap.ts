import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://ghostcode-shah20.vercel.app",
      lastModified: new Date("2026-10-21"),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
