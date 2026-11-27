import type { Metadata } from "next";
import { PricingPage } from "@/features/landing/pricing/PricingPage";
import { PRICING_PATH, PRICING_TEXT } from "@/features/landing/pricing/strings";
import { loadPlanCatalog } from "@/lib/api/planCatalogServer";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: PRICING_TEXT.title,
  description: PRICING_TEXT.lead,
  alternates: { canonical: PRICING_PATH },
};

export default async function PricingRoute() {
  return <PricingPage catalog={await loadPlanCatalog()} />;
}
