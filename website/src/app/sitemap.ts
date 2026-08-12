import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://getarena.vercel.app";

  return [
    { url: baseUrl, lastModified: new Date(), priority: 1.0 },
    { url: `${baseUrl}/pricing`, lastModified: new Date(), priority: 0.8 },
    { url: `${baseUrl}/docs`, lastModified: new Date(), priority: 0.9 },
    { url: `${baseUrl}/docs/commands`, lastModified: new Date(), priority: 0.7 },
    { url: `${baseUrl}/docs/configuration`, lastModified: new Date(), priority: 0.7 },
    { url: `${baseUrl}/docs/formatting`, lastModified: new Date(), priority: 0.7 },
    { url: `${baseUrl}/docs/editorial`, lastModified: new Date(), priority: 0.7 },
    { url: `${baseUrl}/docs/workflows`, lastModified: new Date(), priority: 0.7 },
    { url: `${baseUrl}/docs/troubleshooting`, lastModified: new Date(), priority: 0.6 },
  ];
}
