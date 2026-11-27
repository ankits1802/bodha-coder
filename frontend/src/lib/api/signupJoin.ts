import { setSession } from "@/lib/session/store";
import { isSignedIn } from "./auth";
import { request } from "./client";
import type { IdentityJoinRequest, JoinChoiceRequest, JoinOutcome, JoinPage, LoginResult } from "./types";

export type IdentityJoinResult = LoginResult | JoinOutcome;

export function isJoinOutcome(result: IdentityJoinResult): result is JoinOutcome {
  return "outcome" in result;
}

export function getJoinPage(token: string): Promise<JoinPage> {
  return request<JoinPage>("/api/signup/join/offer", { body: { token }, auth: "none" });
}

export function chooseJoin(body: JoinChoiceRequest): Promise<JoinOutcome> {
  return request<JoinOutcome>("/api/signup/join", { body, auth: "none" });
}

export async function joinWithIdentity(body: IdentityJoinRequest): Promise<IdentityJoinResult> {
  const result = await request<IdentityJoinResult>("/api/signup/identity/join", { body, auth: "none" });
  if (!isJoinOutcome(result) && isSignedIn(result)) setSession(result);
  return result;
}
