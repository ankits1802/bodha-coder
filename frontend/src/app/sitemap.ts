import type { MetadataRoute } from "next";
import { LEGAL_INDEX_PATH, LEGAL_SLUGS, legalPath } from "@/components/shared/legal/legalLinks";
import { LEGAL_DRAFT } from "@/features/legal/config";
import { siteUrl } from "@/lib/site";

function legalEntries(base: string): MetadataRoute.Sitemap {
  if (LEGAL_DRAFT) return [];
  const paths = [LEGAL_INDEX_PATH, ...LEGAL_SLUGS.map(legalPath)];
  return paths.map((path) => ({ url: `${base}${path}`, changeFrequency: "yearly", priority: 0.2 }));
}

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  return [
    { url: base, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/sign-up`, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/sign-in`, changeFrequency: "yearly", priority: 0.3 },
    ...legalEntries(base),
  ];
}
