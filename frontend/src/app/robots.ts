import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

const PRIVATE_PATHS = [
  "/api/",
  "/today",
  "/upload",
  "/queue",
  "/notes/",
  "/compliance",
  "/billing",
  "/remittances",
  "/training",
  "/insights",
  "/quality",
  "/setup",
  "/team",
  "/plan",
  "/security",
  "/settings",
  "/account",
  "/practices/",
  "/help",
  "/hq",
  "/respond",
  "/set-password",
];

export default function robots(): MetadataRoute.Robots {
  return { rules: [{ userAgent: "*", allow: "/", disallow: PRIVATE_PATHS }], sitemap: `${siteUrl()}/sitemap.xml` };
}
