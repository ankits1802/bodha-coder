"use client";

import { getSignInProviders } from "@/lib/api/auth";
import type { SignInProviders } from "@/lib/api/types";
import { useRemote, type Remote } from "./useRemote";

export function useSignInOptions(): Remote<SignInProviders> {
  return useRemote("sign-in-providers", getSignInProviders);
}

export function loadedOptions(remote: Remote<SignInProviders>): SignInProviders | null {
  return remote.state.status === "success" ? remote.state.data : null;
}
