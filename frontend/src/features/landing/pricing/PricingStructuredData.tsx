import type { PlanCatalog } from "@/lib/api/types";
import { siteUrl } from "@/lib/site";
import { pricingJsonLd, scriptSafeJson } from "./pricingJsonLd";
import { PRICING_PATH } from "./strings";

export function PricingStructuredData({ catalog }: { catalog: PlanCatalog }) {
  const data = pricingJsonLd(catalog, `${siteUrl()}${PRICING_PATH}`);
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: scriptSafeJson(data) }} />;
}
