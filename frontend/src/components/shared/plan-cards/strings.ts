import type { BillingInterval } from "@/lib/api/types";

export const PLAN_CARD_TEXT = {
  intervalLabel: "Billing period",
  intervals: { monthly: "Monthly", annual: "Annual" } satisfies Record<BillingInterval, string>,
  monthsFree: (months: number) => `${months} months free`,
  free: "Free",
  trialLength: (days: number) => `for ${days} days`,
  custom: "Custom",
  customUnit: "for larger groups",
  perProvider: { monthly: "per provider / month", annual: "per provider / year" } satisfies Record<BillingInterval, string>,
  users: (count: number | null) => (count === null ? "Unlimited users" : `Up to ${count} users`),
  providers: (count: number | null) => (count === null ? "Unlimited providers" : `Up to ${count} providers`),
  everything: "Every feature included",
} as const;
