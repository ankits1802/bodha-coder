"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { ProviderButtons } from "@/components/shared/sign-in-providers/ProviderButtons";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useSignInOptions } from "@/hooks/useSignInOptions";
import { SIGN_IN_PATH } from "@/lib/api/client";
import type { SignInProviders } from "@/lib/api/types";
import { SignUpForm } from "./SignUpForm";
import { SIGN_UP_TEXT } from "./strings";

const TITLE = "m-0 text-center font-sans text-headline font-semibold tracking-snug";

function Divider() {
  return (
    <div className="flex items-center gap-3 text-footnote text-secondary">
      <span aria-hidden="true" className="h-px flex-1 bg-separator" />
      {SIGN_UP_TEXT.or}
      <span aria-hidden="true" className="h-px flex-1 bg-separator" />
    </div>
  );
}

function CheckEmail({ email }: { email: string }) {
  return (
    <div role="status" className="flex flex-col gap-2 text-center">
      <h2 className={TITLE}>{SIGN_UP_TEXT.checkEmailTitle}</h2>
      <p className="m-0 text-body text-secondary">{email}</p>
    </div>
  );
}

function SignUpChoices({ options }: { options: SignInProviders }) {
  const [sentTo, setSentTo] = useState<string | null>(null);
  if (!options.signup.enabled) return <ErrorState message={SIGN_UP_TEXT.unavailable} />;
  if (sentTo) return <CheckEmail email={sentTo} />;
  return (
    <div className="flex flex-col gap-5">
      <h2 className={TITLE}>{SIGN_UP_TEXT.title}</h2>
      {options.providers.length > 0 ? (
        <>
          <ProviderButtons providers={options.providers} intent="signup" />
          <Divider />
        </>
      ) : null}
      <SignUpForm options={options.signup} onSent={setSentTo} />
    </div>
  );
}

export function SignUpScreen() {
  const options = useSignInOptions();
  const { state } = options;
  return (
    <AuthFrame>
      {state.status === "loading" ? <LoadingState label={SIGN_UP_TEXT.loading} /> : null}
      {state.status === "error" ? (
        <ErrorState message={state.error} retryLabel={SIGN_UP_TEXT.retry} onRetry={options.reload} />
      ) : null}
      {state.status === "success" ? <SignUpChoices options={state.data} /> : null}
      <p className="m-0 text-center text-body text-secondary">
        {SIGN_UP_TEXT.haveAccount}{" "}
        <Link href={SIGN_IN_PATH} className="font-medium text-label underline-offset-2 hover:underline">
          {SIGN_UP_TEXT.signIn}
        </Link>
      </p>
    </AuthFrame>
  );
}
