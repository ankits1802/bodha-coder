import { clearSession, setSession } from "@/lib/session/store";
import { request, requestNothing } from "./client";
import type {
  IdentityProviderName,
  LoginResult,
  MfaChallenge,
  MfaEnrolment,
  MfaVerified,
  SignedIn,
  SignInProviders,
  User,
} from "./types";

export const FORGOT_PASSWORD_PATH = "/forgot-password";
export const SIGN_UP_PATH = "/sign-up";

export function providerStartPath(provider: IdentityProviderName): string {
  return `/api/auth/${provider}/start`;
}

export function mfaReturnPath(challenge: MfaChallenge): string {
  const fragment = new URLSearchParams({ mfa: challenge.mfa_token, setup: challenge.mfa === "setup" ? "1" : "0" });
  return `/sign-in#${fragment.toString()}`;
}

export function isSignedIn(result: LoginResult): result is SignedIn {
  return "access_token" in result;
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const result = await request<LoginResult>("/api/auth/login", { body: { email, password }, auth: "none" });
  if (isSignedIn(result)) setSession(result);
  return result;
}

export function startMfaSetup(mfaToken: string): Promise<MfaEnrolment> {
  return request<MfaEnrolment>("/api/auth/mfa/setup", { body: { mfa_token: mfaToken }, auth: "none" });
}

export function verifyMfa(mfaToken: string, code: string): Promise<MfaVerified> {
  return request<MfaVerified>("/api/auth/mfa/verify", { body: { mfa_token: mfaToken, code }, auth: "none" });
}

export function recoverMfa(mfaToken: string, recoveryCode: string): Promise<SignedIn> {
  return request<SignedIn>("/api/auth/mfa/recover", {
    body: { mfa_token: mfaToken, recovery_code: recoveryCode },
    auth: "none",
  });
}

export function getSignInProviders(): Promise<SignInProviders> {
  return request<SignInProviders>("/api/auth/providers", { auth: "none" });
}

export function requestPasswordReset(email: string): Promise<void> {
  return requestNothing("/api/auth/forgot", { body: { email }, auth: "none" });
}

export async function logout(): Promise<void> {
  try {
    await requestNothing("/api/auth/logout", { method: "POST", auth: "none" });
  } finally {
    clearSession();
  }
}

export function setPassword(token: string, password: string): Promise<void> {
  return requestNothing("/api/auth/password", { body: { token, password }, auth: "none" });
}

export function currentUser(): Promise<User> {
  return request<User>("/api/auth/me");
}
