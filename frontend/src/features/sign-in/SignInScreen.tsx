"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { NEW_PRACTICE_PATH } from "@/lib/api/auth";
import type { User } from "@/lib/api/types";
import { homeFor } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { CredentialsForm } from "./CredentialsForm";
import { MfaSetup } from "./MfaSetup";
import { MfaVerify } from "./MfaVerify";
import { OtherWays } from "./OtherWays";
import { RecoveryCodesStep } from "./RecoveryCodesStep";
import { SIGN_IN_TEXT } from "./strings";
import { useSignInFlow } from "./useSignInFlow";

export function pageAfterSignIn(user: User, next: string | null): string {
  const opensNewPractice = next === NEW_PRACTICE_PATH && user.role !== "hq" && !user.billing_only;
  return opensNewPractice ? NEW_PRACTICE_PATH : homeFor(user);
}

export function SignInScreen() {
  const router = useRouter();
  const { user } = useSession();
  const params = useSearchParams();
  const idle = params.get("reason") === "idle";
  const next = params.get("next");
  const flow = useSignInFlow();
  const { step } = flow;

  useEffect(() => {
    if (user) router.replace(pageAfterSignIn(user, next));
  }, [user, router, next]);

  return (
    <AuthFrame>
      <h2 className="sr-only">{SIGN_IN_TEXT.title}</h2>
      {idle && step.kind === "credentials" ? <InlineAlert tone="warn">{SIGN_IN_TEXT.idle}</InlineAlert> : null}
      {flow.notice && step.kind === "credentials" ? <InlineAlert tone="bad">{flow.notice}</InlineAlert> : null}
      {step.kind === "credentials" ? (
        <div className="flex flex-col gap-3">
          <CredentialsForm
            pending={flow.signIn.pending || user !== null}
            error={flow.signIn.error}
            onSubmit={(email, password) => void flow.submitCredentials(email, password)}
          />
          <OtherWays />
        </div>
      ) : null}
      {step.kind === "finishing" ? <LoadingState label={SIGN_IN_TEXT.finishing} /> : null}
      {step.kind === "setup" ? (
        <MfaSetup
          enrolment={step.enrolment}
          pending={flow.verify.pending}
          error={flow.verify.error}
          onSubmit={(code) => void flow.submitCode(step.mfaToken, code)}
          onCancel={flow.restart}
        />
      ) : null}
      {step.kind === "verify" ? (
        <MfaVerify
          email={step.email}
          code={{
            pending: flow.verify.pending,
            error: flow.verify.error,
            onSubmit: (code) => void flow.submitCode(step.mfaToken, code),
          }}
          recovery={{
            pending: flow.recover.pending,
            error: flow.recover.error,
            onSubmit: (code) => void flow.submitRecoveryCode(step.mfaToken, code),
          }}
          onCancel={flow.restart}
        />
      ) : null}
      {step.kind === "codes" ? (
        <RecoveryCodesStep codes={step.signedIn.recovery_codes ?? []} onContinue={() => flow.keepCodes(step.signedIn)} />
      ) : null}
    </AuthFrame>
  );
}
