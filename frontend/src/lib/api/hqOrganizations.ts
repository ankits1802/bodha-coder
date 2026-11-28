import { request, requestNothing } from "./client";
import type {
  Created,
  HqOrganization,
  HqOrganizationPage,
  NewOrganization,
  OrganizationAdminAppointment,
  OrganizationPurged,
  OrganizationUpdate,
  Plan,
  Renewal,
} from "./types";

const ORGANIZATIONS_PATH = "/api/hq/organizations";

const organizationPath = (organizationId: string, suffix = ""): string =>
  `${ORGANIZATIONS_PATH}/${encodeURIComponent(organizationId)}${suffix}`;

const memberPath = (organizationId: string, kind: "practices" | "admins", memberId: string, suffix = ""): string =>
  organizationPath(organizationId, `/${kind}/${encodeURIComponent(memberId)}${suffix}`);

export function getHqOrganizations(): Promise<HqOrganization[]> {
  return request<HqOrganization[]>(ORGANIZATIONS_PATH);
}

export function addOrganization(body: NewOrganization): Promise<Created> {
  return request<Created>(ORGANIZATIONS_PATH, { body });
}

export function getHqOrganizationPage(organizationId: string): Promise<HqOrganizationPage> {
  return request<HqOrganizationPage>(organizationPath(organizationId));
}

export function updateOrganization(organizationId: string, update: OrganizationUpdate): Promise<void> {
  return requestNothing(organizationPath(organizationId), { method: "PATCH", body: update });
}

export function renewOrganization(organizationId: string, until: string | null, plan: Plan): Promise<Renewal> {
  return request<Renewal>(organizationPath(organizationId, "/renew"), { method: "POST", body: { until, plan } });
}

export function attachPractice(organizationId: string, practiceId: string): Promise<void> {
  return requestNothing(organizationPath(organizationId, "/practices"), { method: "POST", body: { practice_id: practiceId } });
}

export function detachPractice(organizationId: string, practiceId: string): Promise<void> {
  return requestNothing(memberPath(organizationId, "practices", practiceId), { method: "DELETE" });
}

export function setCombinedBilling(organizationId: string, practiceId: string, combined: boolean): Promise<void> {
  return requestNothing(memberPath(organizationId, "practices", practiceId, "/billing"), { method: "PUT", body: { combined } });
}

export function addOrganizationAdmin(organizationId: string, body: OrganizationAdminAppointment): Promise<Created> {
  return request<Created>(organizationPath(organizationId, "/admins"), { body });
}

export function removeOrganizationAdmin(organizationId: string, userId: string): Promise<void> {
  return requestNothing(memberPath(organizationId, "admins", userId), { method: "DELETE" });
}

export function closeOrganization(organizationId: string, confirmName: string): Promise<void> {
  return requestNothing(organizationPath(organizationId, "/close"), { method: "POST", body: { confirm_name: confirmName } });
}

export function purgeOrganization(organizationId: string, confirmName: string): Promise<OrganizationPurged> {
  return request<OrganizationPurged>(organizationPath(organizationId, "/purge"), { body: { confirm_name: confirmName } });
}
