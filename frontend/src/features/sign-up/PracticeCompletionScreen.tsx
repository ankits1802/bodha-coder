"use client";

import { useRouter } from "next/navigation";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useRemote } from "@/hooks/useRemote";
import { useSignInOptions } from "@/hooks/useSignInOptions";
import { SIGN_UP_PATH, isSignedIn, mfaReturnPath } from "@/lib/api/auth";
import { getPendingIdentity } from "@/lib/api/signup";
import type { LoginResult } from "@/lib/api/types";
import { homeFor } from "@/lib/roles";
import { CompletionForm } from "./CompletionForm";
import { openPage } from "./openPage";
import { SIGN_UP_TEXT } from "./strings";

function Expired() {
  return (
    <div className="flex flex-col">
      <ErrorState message={SIGN_UP_TEXT.expired} />
      <ButtonLink href={SIGN_UP_PATH} variant="plain" size="sm" className="self-center">
        {SIGN_UP_TEXT.startAgain}
      </ButtonLink>
    </div>
  );
}

export function PracticeCompletionScreen() {
  const router = useRouter();
  const identity = useRemote("pending-identity", getPendingIdentity);
  const options = useSignInOptions();
  const pending = identity.state;
  const config = options.state;

  function created(result: LoginResult): void {
    if (isSignedIn(result)) router.replace(homeFor(result.user));
    else openPage(mfaReturnPath(result));
  }

  return (
    <AuthFrame>
      <h2 className="m-0 text-center font-sans text-headline font-semibold tracking-snug">{SIGN_UP_TEXT.completeTitle}</h2>
      {pending.status === "loading" || config.status === "loading" ? <LoadingState label={SIGN_UP_TEXT.loading} /> : null}
      {pending.status === "error" ? <Expired /> : null}
      {pending.status === "success" && config.status === "error" ? (
        <ErrorState message={config.error} retryLabel={SIGN_UP_TEXT.retry} onRetry={options.reload} />
      ) : null}
      {pending.status === "success" && config.status === "success" ? (
        <CompletionForm identity={pending.data} options={config.data.signup} onCreated={created} />
      ) : null}
    </AuthFrame>
  );
}
