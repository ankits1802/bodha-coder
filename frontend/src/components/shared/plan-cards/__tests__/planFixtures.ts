import type { PlanCatalog, PlanStatus, PlanSubscription, PlanTerms } from "@/lib/api/types";

export const TRIAL_TERMS: PlanTerms = {
  key: "trial",
  pricing: "free",
  monthly_cents: null,
  annual_cents: null,
  annual_months_free: null,
  max_users: 5,
  max_providers: 2,
};

export const ESSENTIALS_TERMS: PlanTerms = {
  key: "essentials",
  pricing: "per_provider",
  monthly_cents: 14_900,
  annual_cents: 149_000,
  annual_months_free: 2,
  max_users: 5,
  max_providers: 3,
};

export const PROFESSIONAL_TERMS: PlanTerms = {
  key: "professional",
  pricing: "per_provider",
  monthly_cents: 24_900,
  annual_cents: 249_000,
  annual_months_free: 2,
  max_users: null,
  max_providers: 50,
};

export const ENTERPRISE_TERMS: PlanTerms = {
  key: "enterprise",
  pricing: "custom",
  monthly_cents: null,
  annual_cents: null,
  annual_months_free: null,
  max_users: null,
  max_providers: null,
};

export const CATALOG: PlanCatalog = {
  plans: [TRIAL_TERMS, ESSENTIALS_TERMS, PROFESSIONAL_TERMS, ENTERPRISE_TERMS],
  providers: ["stripe", "paypal"],
  trial_days: 14,
};

export function planStatus(changes: Partial<PlanStatus> = {}): PlanStatus {
  return {
    plan: "trial",
    standing: "trial",
    renews_on: "2026-12-02",
    trial_days_left: 3,
    users: 1,
    user_limit: 5,
    providers: 1,
    provider_limit: 2,
    subscription: null,
    ...changes,
  };
}

export function subscription(changes: Partial<PlanSubscription> = {}): PlanSubscription {
  return {
    provider: "stripe",
    interval: "monthly",
    status: "active",
    cancel_at_period_end: false,
    current_period_end: "2027-01-15",
    quantity: 2,
    managed_by: "portal",
    ...changes,
  };
}
