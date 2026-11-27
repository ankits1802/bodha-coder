"use client";

import { useState } from "react";
import { IntervalControl } from "@/components/shared/plan-cards/IntervalControl";
import { mostMonthsFree } from "@/components/shared/plan-cards/planPrice";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import type { BillingInterval, BillingProvider, CheckoutPlan, PlanCatalog } from "@/lib/api/types";
import type { BillingActions } from "./billingActions";
import { initialPlan, isSubscribed, paidPlans, type ChooserStatus } from "./chooserModel";
import { leaveFor } from "./leaveFor";
import { ManageBilling } from "./ManageBilling";
import { PaymentDialog } from "./PaymentDialog";
import { PlanOptions } from "./PlanOptions";
import { PLAN_CHOOSER_TEXT } from "./strings";

interface PlanChooserProps {
  status: ChooserStatus;
  catalog: PlanCatalog;
  actions: BillingActions;
  onChanged: () => void;
}

const words = PLAN_CHOOSER_TEXT;

export function PlanChooser({ status, catalog, actions, onChanged }: PlanChooserProps) {
  const subscription = isSubscribed(status) ? status.subscription : null;
  const [plan, setPlan] = useState<CheckoutPlan>(() => initialPlan(status));
  const [period, setPeriod] = useState<BillingInterval>(status.subscription?.interval ?? "monthly");
  const [paying, setPaying] = useState(false);
  const checkout = useAction(async (provider: BillingProvider) => {
    leaveFor((await actions.checkout({ plan, interval: period, provider })).url);
  });
  const providers = catalog.providers;
  const shown = catalog.plans.filter((terms) => terms.pricing !== "free");

  function choose(): void {
    const [only, ...others] = providers;
    if (only && others.length === 0) void checkout.run(only);
    else setPaying(true);
  }

  return (
    <section aria-labelledby="plans-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="plans-heading" className="m-0 text-title3 font-semibold tracking-headline">
          {words.plansHeading}
        </h2>
        <IntervalControl value={period} onChange={setPeriod} monthsFree={mostMonthsFree(paidPlans(catalog.plans))} />
      </div>
      <PlanOptions
        plans={shown}
        interval={period}
        trialDays={catalog.trial_days}
        current={status.plan}
        chosen={subscription ? null : plan}
        onChoose={setPlan}
      />
      {subscription ? <ManageBilling subscription={subscription} actions={actions} onChanged={onChanged} /> : null}
      {!subscription && checkout.error && !paying ? <InlineAlert tone="bad">{checkout.error}</InlineAlert> : null}
      {!subscription ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" disabled={providers.length === 0} pending={checkout.pending && !paying} onClick={choose}>
            {words.choose}
          </Button>
          {providers.length === 0 ? <span className="text-subhead text-secondary">{words.unavailable}</span> : null}
        </div>
      ) : null}
      <PaymentDialog
        open={paying}
        providers={providers}
        pending={checkout.pending}
        error={checkout.error}
        onClose={() => {
          setPaying(false);
          checkout.clearError();
        }}
        onPay={(provider) => void checkout.run(provider)}
      />
    </section>
  );
}
