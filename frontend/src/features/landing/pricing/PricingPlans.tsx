"use client";

import { useState } from "react";
import { IntervalControl } from "@/components/shared/plan-cards/IntervalControl";
import { PlanCard } from "@/components/shared/plan-cards/PlanCard";
import { mostMonthsFree } from "@/components/shared/plan-cards/planPrice";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { SIGN_UP_PATH } from "@/lib/api/auth";
import type { BillingInterval, PlanCatalog, PlanTerms } from "@/lib/api/types";
import { DemoRequestButton } from "../DemoRequestButton";
import { StartTrialButton } from "../StartTrialButton";
import { LANDING_TEXT } from "../strings";
import { CatalogView } from "./CatalogView";
import { PRICING_TEXT } from "./strings";

function PlanAction({ terms }: { terms: PlanTerms }) {
  if (terms.pricing === "custom") return <DemoRequestButton size="md" />;
  if (terms.pricing === "free") return <StartTrialButton size="md" label={LANDING_TEXT.startTrial} />;
  return (
    <ButtonLink href={SIGN_UP_PATH} size="md">
      {LANDING_TEXT.startTrial}
    </ButtonLink>
  );
}

function PlanGrid({ catalog }: { catalog: PlanCatalog }) {
  const [period, setPeriod] = useState<BillingInterval>("monthly");
  return (
    <div className="flex w-full flex-col items-center gap-8">
      <IntervalControl value={period} onChange={setPeriod} monthsFree={mostMonthsFree(catalog.plans)} />
      <section aria-label={PRICING_TEXT.plansLabel} className="grid w-full gap-5 text-left sm:grid-cols-2 lg:grid-cols-4">
        {catalog.plans.map((terms) => (
          <PlanCard key={terms.key} terms={terms} interval={period} trialDays={catalog.trial_days}>
            <PlanAction terms={terms} />
          </PlanCard>
        ))}
      </section>
    </div>
  );
}

export function PricingPlans({ catalog }: { catalog: PlanCatalog | null }) {
  return <CatalogView catalog={catalog}>{(data) => <PlanGrid catalog={data} />}</CatalogView>;
}
