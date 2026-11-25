import { SIGN_IN_TEXT } from "./strings";

export type GoogleReturn =
  | { kind: "signedIn" }
  | { kind: "mfa"; mfaToken: string; setup: boolean }
  | { kind: "error"; reason: string };

export function googleReturnOf(fragment: string | null | undefined): GoogleReturn | null {
  if (!fragment) return null;
  const params = new URLSearchParams(fragment);
  if (params.has("signed_in")) return { kind: "signedIn" };
  const mfaToken = params.get("mfa");
  if (mfaToken) return { kind: "mfa", mfaToken, setup: params.get("setup") === "1" };
  const reason = params.get("error");
  return reason ? { kind: "error", reason } : null;
}

export function googleErrorText(reason: string): string {
  const errors: Record<string, string> = SIGN_IN_TEXT.googleErrors;
  const known = Object.hasOwn(errors, reason) ? errors[reason] : undefined;
  return known ?? SIGN_IN_TEXT.googleErrors.failed;
}
