import { request, requestNothing } from "./client";
import type {
  AdminMailbox,
  Created,
  DomainClaim,
  DomainClaimRequest,
  DomainJoinRequest,
  JoinRequestRow,
  PracticeRole,
} from "./types";

export type DomainScope = { kind: "practice" } | { kind: "organization"; organizationId: string };

export const PRACTICE_DOMAINS: DomainScope = { kind: "practice" };

export function domainScopeKey(scope: DomainScope): string {
  return scope.kind === "practice" ? "domains:practice" : `domains:organization:${scope.organizationId}`;
}

function domainsPath(scope: DomainScope, claimId?: string, suffix = ""): string {
  const base =
    scope.kind === "practice" ? "/api/practice/domains" : `/api/organizations/${encodeURIComponent(scope.organizationId)}/domains`;
  return claimId === undefined ? base : `${base}/${encodeURIComponent(claimId)}${suffix}`;
}

export function getDomainClaims(scope: DomainScope): Promise<DomainClaim[]> {
  return request<DomainClaim[]>(domainsPath(scope));
}

export function claimDomain(scope: DomainScope, body: DomainClaimRequest): Promise<Created> {
  return request<Created>(domainsPath(scope), { body });
}

export function checkDomainRecord(scope: DomainScope, claimId: string): Promise<void> {
  return requestNothing(domainsPath(scope, claimId, "/check"), { method: "POST" });
}

export function emailDomainAdmin(scope: DomainScope, claimId: string, mailbox: AdminMailbox): Promise<void> {
  return requestNothing(domainsPath(scope, claimId, "/email"), { method: "POST", body: { mailbox } });
}

export function setDomainJoin(scope: DomainScope, claimId: string, body: DomainJoinRequest): Promise<void> {
  return requestNothing(domainsPath(scope, claimId, "/join"), { method: "PUT", body });
}

export function releaseDomain(scope: DomainScope, claimId: string): Promise<void> {
  return requestNothing(domainsPath(scope, claimId), { method: "DELETE" });
}

const joinRequestPath = (requestId: string, action: string): string =>
  `/api/team/join-requests/${encodeURIComponent(requestId)}/${action}`;

export function getJoinRequests(): Promise<JoinRequestRow[]> {
  return request<JoinRequestRow[]>("/api/team/join-requests");
}

export function approveJoinRequest(requestId: string, role: PracticeRole): Promise<Created> {
  return request<Created>(joinRequestPath(requestId, "approve"), { body: { role } });
}

export function declineJoinRequest(requestId: string): Promise<void> {
  return requestNothing(joinRequestPath(requestId, "decline"), { method: "POST" });
}
