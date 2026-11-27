"use client";

import { useId } from "react";
import { PlanCard } from "@/components/shared/plan-cards/PlanCard";
import { OPTION_CARD } from "@/components/ui/RadioOption";
import { StatusDot } from "@/components/ui/StatusDot";
import type { BillingInterval, CheckoutPlan, Plan, PlanTerms } from "@/lib/api/types";
import { PLAN_LABELS } from "@/lib/labels";
import { ContactSales } from "./ContactSales";
import { PLAN_CHOOSER_TEXT } from "./strings";

interface PlanOptionsProps {
  plans: readonly PlanTerms[];
  interval: BillingInterval;
  trialDays: number;
  current: Plan;
  chosen: CheckoutPlan | null;
  onChoose: (plan: CheckoutPlan) => void;
}

interface ChoiceProps {
  terms: PlanTerms;
  interval: BillingInterval;
  trialDays: number;
  group: string;
  checked: boolean;
  current: boolean;
  onChoose: () => void;
}

const GRID = "grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3";

function Choice({ terms, interval, trialDays, group, checked, current, onChoose }: ChoiceProps) {
  const id = useId();
  const label = (
    <label htmlFor={id} className="cursor-pointer after:absolute after:inset-0 after:rounded-panel">
      {PLAN_LABELS[terms.key]}
    </label>
  );
  return (
    <PlanCard terms={terms} interval={interval} trialDays={trialDays} title={label} detailsId={`${id}-details`} className={OPTION_CARD}>
      <input
        id={id}
        type="radio"
        name={group}
        value={terms.key}
        checked={checked}
        onChange={onChoose}
        aria-describedby={`${id}-details`}
        className="sr-only"
      />
      {current ? <StatusDot tone="ok">{PLAN_CHOOSER_TEXT.current}</StatusDot> : null}
    </PlanCard>
  );
}

function isCheckoutPlan(key: Plan): key is CheckoutPlan {
  return key === "essentials" || key === "professional";
}

export function PlanOptions({ plans, interval, trialDays, current, chosen, onChoose }: PlanOptionsProps) {
  const group = useId();
  const cards = plans.map((terms) => {
    const key = terms.key;
    if (chosen !== null && isCheckoutPlan(key)) {
      return (
        <Choice
          key={key}
          terms={terms}
          interval={interval}
          trialDays={trialDays}
          group={group}
          checked={chosen === key}
          current={current === key}
          onChoose={() => onChoose(key)}
        />
      );
    }
    return (
      <PlanCard key={key} terms={terms} interval={interval} trialDays={trialDays}>
        {current === key ? <StatusDot tone="ok">{PLAN_CHOOSER_TEXT.current}</StatusDot> : null}
        {terms.pricing === "custom" ? <ContactSales /> : null}
      </PlanCard>
    );
  });
  if (chosen === null) return <div className={GRID}>{cards}</div>;
  return (
    <fieldset className={`m-0 border-0 p-0 ${GRID}`}>
      <legend className="sr-only">{PLAN_CHOOSER_TEXT.plansLabel}</legend>
      {cards}
    </fieldset>
  );
}
