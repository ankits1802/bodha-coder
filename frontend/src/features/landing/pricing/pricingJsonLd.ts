import { limitLines } from "@/components/shared/plan-cards/planPrice";
import { PLAN_CARD_TEXT } from "@/components/shared/plan-cards/strings";
import { SHARED_TEXT } from "@/components/shared/strings";
import type { BillingInterval, PlanCatalog, PlanTerms } from "@/lib/api/types";
import { PLAN_LABELS } from "@/lib/labels";

type JsonLd = Record<string, unknown>;

const CURRENCY = "USD";
const INTERVALS: readonly BillingInterval[] = ["monthly", "annual"];
const UNIT_CODES: Record<BillingInterval, string> = { monthly: "MON", annual: "ANN" };

function centsFor(terms: PlanTerms, interval: BillingInterval): number | null {
  return interval === "monthly" ? terms.monthly_cents : terms.annual_cents;
}

function offerFor(terms: PlanTerms, interval: BillingInterval, pageUrl: string): JsonLd[] {
  const cents = centsFor(terms, interval);
  if (cents === null) return [];
  const price = (cents / 100).toFixed(2);
  return [
    {
      "@type": "Offer",
      url: pageUrl,
      price,
      priceCurrency: CURRENCY,
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price,
        priceCurrency: CURRENCY,
        unitText: PLAN_CARD_TEXT.perProvider[interval],
        referenceQuantity: { "@type": "QuantitativeValue", value: 1, unitCode: UNIT_CODES[interval] },
      },
    },
  ];
}

function productFor(terms: PlanTerms, pageUrl: string): JsonLd[] {
  if (terms.pricing !== "per_provider") return [];
  const offers = INTERVALS.flatMap((interval) => offerFor(terms, interval, pageUrl));
  if (offers.length === 0) return [];
  return [
    {
      "@type": "Product",
      name: `${SHARED_TEXT.brand} ${PLAN_LABELS[terms.key]}`,
      description: limitLines(terms).join(". "),
      brand: { "@type": "Brand", name: SHARED_TEXT.brand },
      offers,
    },
  ];
}

export function pricingJsonLd(catalog: PlanCatalog, pageUrl: string): JsonLd {
  return { "@context": "https://schema.org", "@graph": catalog.plans.flatMap((terms) => productFor(terms, pageUrl)) };
}

export function scriptSafeJson(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
