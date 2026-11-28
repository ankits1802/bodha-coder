"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { FORGOT_PASSWORD_PATH } from "@/lib/api/auth";
import { QUIET_LINK, QuietButton } from "./QuietButton";
import { SIGN_IN_TEXT } from "./strings";
import { useSsoDiscovery } from "./useSsoDiscovery";

interface CredentialsFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (email: string, password: string) => void;
  onSingleSignOn: (startUrl: string) => void;
}

const FIELD = "flex h-14 flex-col justify-center gap-px bg-surface px-4";
const LABEL = "text-caption text-tertiary";
const TEXT = "w-full border-0 bg-transparent text-input tracking-snug text-label outline-none";
const INPUT = `${TEXT} p-0`;
const PASSWORD = `${TEXT} py-0 pl-0`;

export function CredentialsForm({ pending, error, onSubmit, onSingleSignOn }: CredentialsFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [missing, setMissing] = useState(false);
  const [passwordFor, setPasswordFor] = useState<string | null>(null);
  const sso = useSsoDiscovery(email);
  const address = email.trim().toLowerCase();
  const startUrl = sso.start_url;
  const ssoOnly = sso.mode === "required" && startUrl !== null && passwordFor !== address;

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (ssoOnly && startUrl !== null) {
      onSingleSignOn(startUrl);
      return;
    }
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
        {ssoOnly ? null : (
          <>
            <div aria-hidden="true" className="ml-4 h-px bg-separator" />
            <div className={FIELD}>
              <label htmlFor="sign-in-password" className={LABEL}>
                {SIGN_IN_TEXT.password}
              </label>
              <PasswordInput
                id="sign-in-password"
                look="bare"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={PASSWORD}
              />
            </div>
          </>
        )}
      </div>
      {missing && !ssoOnly ? <InlineAlert tone="bad">{SIGN_IN_TEXT.missingDetails}</InlineAlert> : null}
      {error && !missing ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={pending} className="w-full">
        {ssoOnly ? SIGN_IN_TEXT.continueWithSso : SIGN_IN_TEXT.continue}
      </Button>
      {!ssoOnly && startUrl !== null ? (
        <Button size="lg" className="w-full" onClick={() => onSingleSignOn(startUrl)}>
          {SIGN_IN_TEXT.continueWithSso}
        </Button>
      ) : null}
      {ssoOnly ? (
        <QuietButton onClick={() => setPasswordFor(address)}>{SIGN_IN_TEXT.usePassword}</QuietButton>
      ) : (
        <Link href={FORGOT_PASSWORD_PATH} className={QUIET_LINK}>
          {SIGN_IN_TEXT.forgotPassword}
        </Link>
      )}
    </form>
  );
}
