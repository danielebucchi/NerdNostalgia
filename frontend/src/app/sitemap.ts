import type { MetadataRoute } from "next";
import { listArticles, listWantedItems } from "@/lib/api";
import { SITE_URL } from "@/lib/seo";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    {
      url: `${SITE_URL}/`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${SITE_URL}/cerco-compro`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/contatti`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${SITE_URL}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.2,
    },
    {
      url: `${SITE_URL}/cookie-policy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.2,
    },
  ];

  const articleEntries: MetadataRoute.Sitemap = [];
  try {
    const data = await listArticles({ status: "PUBLISHED", limit: 100 });
    for (const a of data.items) {
      articleEntries.push({
        url: `${SITE_URL}/articles/${a.id}`,
        lastModified: a.updated_at ? new Date(a.updated_at) : now,
        changeFrequency: "weekly",
        priority: 0.9,
      });
    }
  } catch {
    // backend irraggiungibile in build: meglio una sitemap minima che un errore
  }

  const wantedEntries: MetadataRoute.Sitemap = [];
  try {
    const data = await listWantedItems({ status: "ACTIVE", limit: 100 });
    for (const w of data.items) {
      wantedEntries.push({
        url: `${SITE_URL}/cerco-compro/${w.id}`,
        lastModified: w.updated_at ? new Date(w.updated_at) : now,
        changeFrequency: "weekly",
        priority: 0.6,
      });
    }
  } catch {
    // idem
  }

  return [...staticPages, ...articleEntries, ...wantedEntries];
}
