"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { FORGOT_PASSWORD_PATH } from "@/lib/api/auth";
import { QUIET_LINK } from "./QuietButton";
import { SIGN_IN_TEXT } from "./strings";

interface CredentialsFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (email: string, password: string) => void;
}

const FIELD = "flex h-14 flex-col justify-center gap-px bg-surface px-4";
const LABEL = "text-caption text-tertiary";
const INPUT = "border-0 bg-transparent p-0 text-input tracking-snug text-label outline-none";

export function CredentialsForm({ pending, error, onSubmit }: CredentialsFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [missing, setMissing] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const ready = email.trim() !== "" && password !== "";
    setMissing(!ready);
    if (ready) onSubmit(email.trim(), password);
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-5">
      <div className="overflow-hidden rounded-input-group shadow-field focus-within:shadow-field-focus">
        <div className={FIELD}>
          <label htmlFor="sign-in-email" className={LABEL}>
            {SIGN_IN_TEXT.email}
          </label>
          <input
            id="sign-in-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={INPUT}
          />
        </div>
        <div aria-hidden="true" className="ml-4 h-px bg-separator" />
        <div className={FIELD}>
          <label htmlFor="sign-in-password" className={LABEL}>
            {SIGN_IN_TEXT.password}
          </label>
          <input
            id="sign-in-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={INPUT}
          />
        </div>
      </div>
      {missing ? <InlineAlert tone="bad">{SIGN_IN_TEXT.missingDetails}</InlineAlert> : null}
      {error && !missing ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={pending} className="w-full">
        {SIGN_IN_TEXT.continue}
      </Button>
      <Link href={FORGOT_PASSWORD_PATH} className={QUIET_LINK}>
        {SIGN_IN_TEXT.forgotPassword}
      </Link>
    </form>
  );
}
