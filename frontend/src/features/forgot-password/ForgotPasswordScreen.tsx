"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { requestPasswordReset } from "@/lib/api/auth";
import { SIGN_IN_PATH } from "@/lib/api/client";
import { isEmail } from "@/lib/validation";
import { FORGOT_PASSWORD_TEXT } from "./strings";

function Sent() {
  return (
    <div className="flex flex-col gap-5">
      <InlineAlert tone="ok">{FORGOT_PASSWORD_TEXT.sent}</InlineAlert>
      <ButtonLink href={SIGN_IN_PATH} variant="primary" size="lg" className="w-full">
        {FORGOT_PASSWORD_TEXT.backToSignIn}
      </ButtonLink>
    </div>
  );
}

export function ForgotPasswordScreen() {
  const [email, setEmail] = useState("");
  const [invalid, setInvalid] = useState(false);
  const [sent, setSent] = useState(false);
  const send = useAction(requestPasswordReset);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const ready = isEmail(email);
    setInvalid(!ready);
    if (!ready) return;
    const outcome = await send.run(email.trim());
    if (outcome.ok) setSent(true);
  }

  return (
    <AuthFrame>
      {sent ? (
        <Sent />
      ) : (
        <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-4">
          <h2 className="m-0 text-center font-sans text-headline font-semibold tracking-snug">
            {FORGOT_PASSWORD_TEXT.title}
          </h2>
          <Field label={FORGOT_PASSWORD_TEXT.email} error={invalid ? FORGOT_PASSWORD_TEXT.invalidEmail : null}>
            {(control) => (
              <Input
                {...control}
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            )}
          </Field>
          {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
          <Button type="submit" variant="primary" size="lg" pending={send.pending} className="mt-1 w-full">
            {FORGOT_PASSWORD_TEXT.send}
          </Button>
          <Link
            href={SIGN_IN_PATH}
            className="self-center rounded-control px-2 py-1 text-body text-secondary hover:text-label"
          >
            {FORGOT_PASSWORD_TEXT.backToSignIn}
          </Link>
        </form>
      )}
    </AuthFrame>
  );
}
