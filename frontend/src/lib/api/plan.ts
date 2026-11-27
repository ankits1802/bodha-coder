import { request, requestNothing } from "./client";
import type { CheckoutRequest, PlanCatalog, PlanStatus, RedirectLink } from "./types";

export function getPlanCatalog(): Promise<PlanCatalog> {
  return request<PlanCatalog>("/api/plans", { auth: "none" });
}

export function getPlanStatus(): Promise<PlanStatus> {
  return request<PlanStatus>("/api/plan");
}

export function startCheckout(body: CheckoutRequest): Promise<RedirectLink> {
  return request<RedirectLink>("/api/plan/checkout", { body });
}

export function openBillingPortal(): Promise<RedirectLink> {
  return request<RedirectLink>("/api/plan/portal", { method: "POST" });
}

export function cancelSubscription(): Promise<void> {
  return requestNothing("/api/plan/cancel", { method: "POST" });
}
