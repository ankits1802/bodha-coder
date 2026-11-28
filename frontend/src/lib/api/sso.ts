import { request } from "./client";
import type { DomainScope } from "./domains";
import type {
  SsoDiscovery,
  SsoIdentityProvider,
  SsoMetadataRequest,
  SsoSettings,
  SsoSettingsRequest,
  SsoTrialLink,
  SsoTrialResult,
} from "./types";

export const SSO_TEST_FRAGMENT = "sso_test";

export function ssoScopeKey(scope: DomainScope): string {
  return scope.kind === "practice" ? "sso:practice" : `sso:organization:${scope.organizationId}`;
}

function ssoPath(scope: DomainScope, suffix = ""): string {
  const base =
    scope.kind === "practice" ? "/api/practice/sso" : `/api/organizations/${encodeURIComponent(scope.organizationId)}/sso`;
  return `${base}${suffix}`;
}

export function getSso(scope: DomainScope): Promise<SsoSettings> {
  return request<SsoSettings>(ssoPath(scope));
}

export function setUpSso(scope: DomainScope): Promise<SsoSettings> {
  return request<SsoSettings>(ssoPath(scope), { method: "POST" });
}

export function saveSso(scope: DomainScope, body: SsoSettingsRequest): Promise<SsoSettings> {
  return request<SsoSettings>(ssoPath(scope), { method: "PUT", body });
}

export function removeSso(scope: DomainScope): Promise<SsoSettings> {
  return request<SsoSettings>(ssoPath(scope), { method: "DELETE" });
}

export function readSsoMetadata(scope: DomainScope, body: SsoMetadataRequest): Promise<SsoIdentityProvider> {
  return request<SsoIdentityProvider>(ssoPath(scope, "/metadata"), { body });
}

export function startSsoTest(scope: DomainScope): Promise<SsoTrialLink> {
  return request<SsoTrialLink>(ssoPath(scope, "/test"), { method: "POST" });
}

export function readSsoTestResult(scope: DomainScope, token: string): Promise<SsoTrialResult> {
  return request<SsoTrialResult>(ssoPath(scope, "/test-result"), { body: { token } });
}

export function discoverSso(email: string): Promise<SsoDiscovery> {
  return request<SsoDiscovery>("/api/auth/sso", { body: { email }, auth: "none" });
}
