import { setSession } from "@/lib/session/store";
import { isSignedIn } from "./auth";
import { request, requestNothing } from "./client";
import type { IdentitySignupRequest, LoginResult, PendingIdentity, SignupRequest } from "./types";

export function requestSignup(body: SignupRequest): Promise<void> {
  return requestNothing("/api/signup", { body, auth: "none" });
}

export function getPendingIdentity(): Promise<PendingIdentity> {
  return request<PendingIdentity>("/api/signup/identity", { auth: "none" });
}

export async function completeIdentitySignup(body: IdentitySignupRequest): Promise<LoginResult> {
  const result = await request<LoginResult>("/api/signup/identity", { body, auth: "none" });
  if (isSignedIn(result)) setSession(result);
  return result;
}
