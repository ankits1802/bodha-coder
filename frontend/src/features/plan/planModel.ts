import type { StatusTone } from "@/components/ui/StatusDot";
import type { BillingStatus, CheckoutPlan, PlanStanding, PlanStatus, PlanTerms } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { PLAN_TEXT } from "./strings";

export interface DateFact {
  label: string;
  value: string;
}

const STANDING_TONES: Record<PlanStanding, StatusTone> = {
  trial: "low",
  active: "ok",
  past_due: "warn",
  canceling: "warn",
  canceled: "bad",
  ended: "bad",
  managed: "ok",
};

const LIVE: readonly BillingStatus[] = ["active", "past_due"];
const words = PLAN_TEXT;

export function standingView(standing: PlanStanding): { tone: StatusTone; label: string } {
  return { tone: STANDING_TONES[standing], label: words.standings[standing] };
}

export function dateFact(status: PlanStatus): DateFact | null {
  if (!status.renews_on) return null;
  const value = formatCalendarDay(status.renews_on, "year");
  if (status.standing === "trial") return { label: words.facts.trialEnds, value };
  if (status.standing === "past_due") return { label: words.facts.accessUntil, value };
  if (status.standing === "canceling" || status.standing === "canceled") return { label: words.facts.ends, value };
  if (status.standing === "ended") return { label: words.facts.ended, value };
  return { label: words.facts.renews, value };
}

export function isSubscribed(status: PlanStatus): boolean {
  return status.subscription !== null && LIVE.includes(status.subscription.status);
}

export function paidPlans(plans: readonly PlanTerms[]): PlanTerms[] {
  return plans.filter((plan) => plan.pricing === "per_provider");
}

export function initialPlan(status: PlanStatus): CheckoutPlan {
  return status.plan === "professional" ? "professional" : "essentials";
}
