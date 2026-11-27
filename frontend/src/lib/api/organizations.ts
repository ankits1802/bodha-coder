import { request, requestNothing } from "./client";
import type {
  AccessRequest,
  CheckoutRequest,
  Created,
  InsightDays,
  LocationRequest,
  OrganizationInsights,
  OrganizationOverview,
  OrganizationPersonRequest,
  OrganizationPlan,
  RedirectLink,
} from "./types";

const apiPath = (organizationId: string, suffix = ""): string => `/api/organizations/${encodeURIComponent(organizationId)}${suffix}`;

const practicePath = (organizationId: string, practiceId: string, suffix: string): string =>
  apiPath(organizationId, `/practices/${encodeURIComponent(practiceId)}${suffix}`);

export function getOrganization(organizationId: string): Promise<OrganizationOverview> {
  return request<OrganizationOverview>(apiPath(organizationId));
}

export function addLocation(organizationId: string, body: LocationRequest): Promise<Created> {
  return request<Created>(apiPath(organizationId, "/practices"), { body });
}

export function setCombinedBilling(organizationId: string, practiceId: string, combined: boolean): Promise<void> {
  return requestNothing(practicePath(organizationId, practiceId, "/billing"), { method: "PUT", body: { combined } });
}

export function grantOwnAccess(organizationId: string, practiceId: string, body: AccessRequest): Promise<void> {
  return requestNothing(practicePath(organizationId, practiceId, "/access"), { method: "POST", body });
}

export function addOrganizationPerson(organizationId: string, body: OrganizationPersonRequest): Promise<Created> {
  return request<Created>(apiPath(organizationId, "/people"), { body });
}

export function getOrganizationInsights(organizationId: string, days: InsightDays): Promise<OrganizationInsights> {
  return request<OrganizationInsights>(apiPath(organizationId, "/insights"), { query: { days } });
}

export function getOrganizationPlan(organizationId: string): Promise<OrganizationPlan> {
  return request<OrganizationPlan>(apiPath(organizationId, "/plan"));
}

export function startOrganizationCheckout(organizationId: string, body: CheckoutRequest): Promise<RedirectLink> {
  return request<RedirectLink>(apiPath(organizationId, "/plan/checkout"), { body });
}

export function openOrganizationPortal(organizationId: string): Promise<RedirectLink> {
  return request<RedirectLink>(apiPath(organizationId, "/plan/portal"), { method: "POST" });
}

export function cancelOrganizationSubscription(organizationId: string): Promise<void> {
  return requestNothing(apiPath(organizationId, "/plan/cancel"), { method: "POST" });
}
