import { isSignedIn, mfaReturnPath } from "@/lib/api/auth";
import type { LoginResult } from "@/lib/api/types";
import { homeFor } from "@/lib/roles";

export function pageAfter(result: LoginResult): string {
  return isSignedIn(result) ? homeFor(result.user) : mfaReturnPath(result);
}

export function enterPractice(result: LoginResult): void {
  window.location.assign(pageAfter(result));
}
