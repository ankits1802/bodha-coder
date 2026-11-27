import type { BillingInterval, PlanTerms } from "@/lib/api/types";
import { formatWholeDollars } from "@/lib/format";
import { PLAN_CARD_TEXT } from "./strings";

export interface CardPrice {
  amount: string;
  unit: string;
}

const words = PLAN_CARD_TEXT;

export function cardPrice(terms: PlanTerms, interval: BillingInterval, trialDays: number): CardPrice {
  if (terms.pricing === "free") return { amount: words.free, unit: words.trialLength(trialDays) };
  const cents = interval === "monthly" ? terms.monthly_cents : terms.annual_cents;
  if (terms.pricing === "custom" || cents === null) return { amount: words.custom, unit: words.customUnit };
  return { amount: formatWholeDollars(cents), unit: words.perProvider[interval] };
}

export function limitLines(terms: PlanTerms): string[] {
  return [words.users(terms.max_users), words.providers(terms.max_providers), words.everything];
}

export function mostMonthsFree(plans: readonly PlanTerms[]): number | null {
  const months = plans.map((plan) => plan.annual_months_free).filter((value): value is number => value !== null && value > 0);
  return months.length > 0 ? Math.max(...months) : null;
}
