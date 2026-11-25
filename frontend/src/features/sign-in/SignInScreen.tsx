"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { isSignedIn, login, startMfaSetup, verifyMfa } from "@/lib/api/auth";
import type { MfaEnrolment } from "@/lib/api/types";
import { homeFor } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { CredentialsForm } from "./CredentialsForm";
import { MfaSetup } from "./MfaSetup";
import { MfaVerify } from "./MfaVerify";
import { SIGN_IN_TEXT } from "./strings";

type Step =
  | { kind: "credentials" }
  | { kind: "setup"; mfaToken: string; enrolment: MfaEnrolment }
  | { kind: "verify"; mfaToken: string; email: string };

async function signInStep(email: string, password: string): Promise<Step> {
  const result = await login(email, password);
  if (isSignedIn(result)) return { kind: "credentials" };
  if (result.mfa === "verify") return { kind: "verify", mfaToken: result.mfa_token, email };
  return { kind: "setup", mfaToken: result.mfa_token, enrolment: await startMfaSetup(result.mfa_token) };
}

export function SignInScreen() {
  const router = useRouter();
  const { user } = useSession();
  const idle = useSearchParams().get("reason") === "idle";
  const [step, setStep] = useState<Step>({ kind: "credentials" });
  const signIn = useAction(signInStep);
  const verify = useAction(verifyMfa);

  useEffect(() => {
    if (user) router.replace(homeFor(user.role));
  }, [user, router]);

  async function submitCredentials(email: string, password: string): Promise<void> {
    const outcome = await signIn.run(email, password);
    if (outcome.ok) setStep(outcome.value);
  }

  function restart(): void {
    verify.clearError();
    signIn.clearError();
    setStep({ kind: "credentials" });
  }

  return (
    <AuthFrame>
      <h2 className="sr-only">{SIGN_IN_TEXT.title}</h2>
      {idle && step.kind === "credentials" ? <InlineAlert tone="warn">{SIGN_IN_TEXT.idle}</InlineAlert> : null}
      {step.kind === "credentials" ? (
        <CredentialsForm pending={signIn.pending || user !== null} error={signIn.error} onSubmit={submitCredentials} />
      ) : null}
      {step.kind === "setup" ? (
        <MfaSetup
          enrolment={step.enrolment}
          pending={verify.pending}
          error={verify.error}
          onSubmit={(code) => void verify.run(step.mfaToken, code)}
          onCancel={restart}
        />
      ) : null}
      {step.kind === "verify" ? (
        <MfaVerify
          email={step.email}
          pending={verify.pending}
          error={verify.error}
          onSubmit={(code) => void verify.run(step.mfaToken, code)}
          onCancel={restart}
        />
      ) : null}
    </AuthFrame>
  );
}
