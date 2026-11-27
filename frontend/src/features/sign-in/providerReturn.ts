import { providerName } from "@/components/shared/sign-in-providers/ProviderButtons";
import { SHARED_TEXT } from "@/components/shared/strings";
import type { IdentityProviderName } from "@/lib/api/types";
import { SIGN_IN_TEXT } from "./strings";

export type ProviderReturn =
  | { kind: "signedIn" }
  | { kind: "mfa"; mfaToken: string; setup: boolean }
  | { kind: "error"; reason: string; provider: IdentityProviderName | null };

type ErrorReason = keyof typeof SIGN_IN_TEXT.providerErrors;

function knownProvider(value: string | null): IdentityProviderName | null {
  return value !== null && Object.hasOwn(SHARED_TEXT.identityProviders.names, value) ? (value as IdentityProviderName) : null;
}

export function providerReturnOf(fragment: string | null | undefined): ProviderReturn | null {
  if (!fragment) return null;
  const params = new URLSearchParams(fragment);
  if (params.has("signed_in")) return { kind: "signedIn" };
  const mfaToken = params.get("mfa");
  if (mfaToken) return { kind: "mfa", mfaToken, setup: params.get("setup") === "1" };
  const reason = params.get("error");
  return reason ? { kind: "error", reason, provider: knownProvider(params.get("provider")) } : null;
}

export function providerErrorText(reason: string, provider: IdentityProviderName | null): string {
  const errors = SIGN_IN_TEXT.providerErrors;
  const known: ErrorReason = Object.hasOwn(errors, reason) ? (reason as ErrorReason) : "failed";
  return errors[known](provider ? providerName(provider) : null);
}
