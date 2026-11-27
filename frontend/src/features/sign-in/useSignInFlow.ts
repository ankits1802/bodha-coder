"use client";

import { useEffect, useRef, useState } from "react";
import { useAction } from "@/hooks/useAction";
import { useFragmentToken } from "@/hooks/useFragmentToken";
import { isSignedIn, login, recoverMfa, startMfaSetup, verifyMfa } from "@/lib/api/auth";
import { refreshSession } from "@/lib/api/client";
import { UserFacingError, messageOf } from "@/lib/api/errors";
import type { MfaEnrolment, MfaVerified, SignedIn } from "@/lib/api/types";
import { setSession } from "@/lib/session/store";
import { providerErrorText, providerReturnOf, type ProviderReturn } from "./providerReturn";

export type Step =
  | { kind: "credentials" }
  | { kind: "finishing" }
  | { kind: "setup"; mfaToken: string; enrolment: MfaEnrolment }
  | { kind: "verify"; mfaToken: string; email: string | null }
  | { kind: "codes"; signedIn: MfaVerified };

async function signInStep(email: string, password: string): Promise<Step> {
  const result = await login(email, password);
  if (isSignedIn(result)) return { kind: "credentials" };
  if (result.mfa === "verify") return { kind: "verify", mfaToken: result.mfa_token, email };
  return { kind: "setup", mfaToken: result.mfa_token, enrolment: await startMfaSetup(result.mfa_token) };
}

function stepAfterProvider(returned: ProviderReturn | null): Step {
  if (returned?.kind === "mfa" && !returned.setup) return { kind: "verify", mfaToken: returned.mfaToken, email: null };
  if (returned?.kind === "mfa" || returned?.kind === "signedIn") return { kind: "finishing" };
  return { kind: "credentials" };
}

async function finishProvider(returned: ProviderReturn): Promise<Step | null> {
  if (returned.kind === "mfa") {
    return { kind: "setup", mfaToken: returned.mfaToken, enrolment: await startMfaSetup(returned.mfaToken) };
  }
  if (!(await refreshSession())) throw new UserFacingError(providerErrorText("failed", null));
  return null;
}

function needsFinishing(returned: ProviderReturn | null): returned is ProviderReturn {
  return returned?.kind === "signedIn" || (returned?.kind === "mfa" && returned.setup);
}

export function useSignInFlow() {
  const fragment = useFragmentToken();
  const returned = providerReturnOf(fragment);
  const [chosen, setChosen] = useState<Step | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const finishing = useRef(false);
  const signIn = useAction(signInStep);
  const verify = useAction(verifyMfa);
  const recover = useAction(recoverMfa);

  useEffect(() => {
    const pending = providerReturnOf(fragment);
    if (finishing.current || !needsFinishing(pending)) return;
    finishing.current = true;
    finishProvider(pending).then(
      (step) => {
        if (step) setChosen(step);
      },
      (error: unknown) => setFailure(messageOf(error)),
    );
  }, [fragment]);

  async function submitCredentials(email: string, password: string): Promise<void> {
    const outcome = await signIn.run(email, password);
    if (outcome.ok) setChosen(outcome.value);
  }

  async function submitCode(mfaToken: string, code: string): Promise<void> {
    const outcome = await verify.run(mfaToken, code);
    if (!outcome.ok) return;
    if (outcome.value.recovery_codes?.length) setChosen({ kind: "codes", signedIn: outcome.value });
    else setSession(outcome.value);
  }

  async function submitRecoveryCode(mfaToken: string, recoveryCode: string): Promise<void> {
    const outcome = await recover.run(mfaToken, recoveryCode);
    if (outcome.ok) setSession(outcome.value);
  }

  function restart(): void {
    verify.clearError();
    signIn.clearError();
    recover.clearError();
    setFailure(null);
    setChosen({ kind: "credentials" });
  }

  const step: Step = chosen ?? (failure ? { kind: "credentials" } : stepAfterProvider(returned));
  const providerError =
    chosen === null && returned?.kind === "error" ? providerErrorText(returned.reason, returned.provider) : null;
  return {
    step,
    notice: failure ?? providerError,
    signIn,
    verify,
    recover,
    submitCredentials,
    submitCode,
    submitRecoveryCode,
    keepCodes: (signedIn: SignedIn) => setSession(signedIn),
    restart,
  };
}
