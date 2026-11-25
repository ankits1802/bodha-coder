"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { PASSWORD_MIN_LENGTH } from "@/lib/validation";
import { SET_PASSWORD_TEXT } from "./strings";

interface PasswordFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (password: string) => void;
}

interface Problems {
  password: string | null;
  confirm: string | null;
}

function problemsOf(password: string, confirm: string): Problems {
  return {
    password: password.length < PASSWORD_MIN_LENGTH ? SET_PASSWORD_TEXT.tooShort(PASSWORD_MIN_LENGTH) : null,
    confirm: confirm !== password ? SET_PASSWORD_TEXT.mismatch : null,
  };
}

export function PasswordForm({ pending, error, onSubmit }: PasswordFormProps) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [problems, setProblems] = useState<Problems>({ password: null, confirm: null });

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const found = problemsOf(password, confirm);
    setProblems(found);
    if (!found.password && !found.confirm) onSubmit(password);
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <h2 className="m-0 text-center font-sans text-headline font-semibold tracking-snug">{SET_PASSWORD_TEXT.title}</h2>
      <Field label={SET_PASSWORD_TEXT.password} error={problems.password}>
        {(control) => (
          <Input
            {...control}
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        )}
      </Field>
      <Field label={SET_PASSWORD_TEXT.confirm} error={problems.confirm}>
        {(control) => (
          <Input
            {...control}
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
          />
        )}
      </Field>
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={pending} className="mt-1 w-full">
        {SET_PASSWORD_TEXT.submit}
      </Button>
    </form>
  );
}
