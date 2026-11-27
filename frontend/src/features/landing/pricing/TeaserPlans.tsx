"use client";

import { cardPrice } from "@/components/shared/plan-cards/planPrice";
import type { PlanCatalog, PlanTerms } from "@/lib/api/types";
import { PLAN_LABELS } from "@/lib/labels";
import { cssVars } from "../motion/cssVars";
import { CatalogView } from "./CatalogView";
import { PRICING_TEXT } from "./strings";

function TeaserPlan({ terms, trialDays, index }: { terms: PlanTerms; trialDays: number; index: number }) {
  const price = cardPrice(terms, "monthly", trialDays);
  return (
    <li data-reveal="" style={cssVars({ "--delay": `${index * 90}ms` })} className="flex min-w-0 flex-col rounded-panel bg-surface p-5 shadow-panel">
      <h3 className="m-0 text-headline font-semibold tracking-headline">{PLAN_LABELS[terms.key]}</h3>
      <p className="mt-3 mb-0 flex flex-col">
        <span className="text-stat font-bold tracking-title tabular-nums">{price.amount}</span>
        <span className="text-footnote text-secondary">{price.unit}</span>
      </p>
      {terms.pricing === "free" ? <p className="mt-1 mb-0 text-footnote text-secondary">{PRICING_TEXT.teaser.noCard}</p> : null}
    </li>
  );
}

function PlanList({ catalog }: { catalog: PlanCatalog }) {
  const listed = catalog.plans.filter((terms) => terms.pricing !== "custom");
  return (
    <ul aria-label={PRICING_TEXT.plansLabel} className="m-0 grid list-none gap-3 p-0 sm:grid-cols-3">
      {listed.map((terms, index) => (
        <TeaserPlan key={terms.key} terms={terms} trialDays={catalog.trial_days} index={index} />
      ))}
    </ul>
  );
}

export function TeaserPlans({ catalog }: { catalog: PlanCatalog | null }) {
  return <CatalogView catalog={catalog}>{(data) => <PlanList catalog={data} />}</CatalogView>;
}
