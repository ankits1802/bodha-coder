"use client";

import { useState } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { useAction } from "@/hooks/useAction";
import { useFragmentToken } from "@/hooks/useFragmentToken";
import { FORGOT_PASSWORD_PATH, setPassword } from "@/lib/api/auth";
import { SIGN_IN_PATH } from "@/lib/api/client";
import { PasswordForm } from "./PasswordForm";
import { SET_PASSWORD_TEXT } from "./strings";

function Done() {
  return (
    <div className="flex flex-col gap-5">
      <InlineAlert tone="ok">{SET_PASSWORD_TEXT.done}</InlineAlert>
      <ButtonLink href={SIGN_IN_PATH} variant="primary" size="lg" className="w-full">
        {SET_PASSWORD_TEXT.signIn}
      </ButtonLink>
    </div>
  );
}

function NewLink() {
  return (
    <ButtonLink href={FORGOT_PASSWORD_PATH} variant="plain" size="sm" className="self-center">
      {SET_PASSWORD_TEXT.newLink}
    </ButtonLink>
  );
}

function Content({ token }: { token: string | null | undefined }) {
  const save = useAction(setPassword);
  const [done, setDone] = useState(false);

  async function submit(password: string): Promise<void> {
    if (!token) return;
    const outcome = await save.run(token, password);
    if (outcome.ok) setDone(true);
  }

  if (token === undefined) return <LoadingState label={SET_PASSWORD_TEXT.loading} />;
  if (token === null) {
    return (
      <div className="flex flex-col">
        <ErrorState message={SET_PASSWORD_TEXT.invalidLink} />
        <NewLink />
      </div>
    );
  }
  if (done) return <Done />;
  return (
    <div className="flex flex-col gap-3">
      <PasswordForm pending={save.pending} error={save.error} onSubmit={(value) => void submit(value)} />
      {save.error ? <NewLink /> : null}
    </div>
  );
}

export function SetPasswordScreen() {
  const token = useFragmentToken();
  return (
    <AuthFrame>
      <Content token={token} />
    </AuthFrame>
  );
}
