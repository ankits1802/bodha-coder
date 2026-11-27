import { request } from "./client";
import type { VerifiedDomain } from "./types";

export function verifyDomainLink(token: string): Promise<VerifiedDomain> {
  return request<VerifiedDomain>("/api/domain-verifications", { body: { token }, auth: "none" });
}
