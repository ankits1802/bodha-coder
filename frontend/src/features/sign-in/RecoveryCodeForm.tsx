"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import type { Alternative } from "./CodeForm";
import { QuietButton } from "./QuietButton";
import { SIGN_IN_TEXT } from "./strings";

export const RECOVERY_CODE_CHARACTERS = 16;

interface RecoveryCodeFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (recoveryCode: string) => void;
  onCancel: () => void;
  alternative: Alternative;
}

function characterCount(text: string): number {
  return text.replace(/[\s-]/g, "").length;
}

export function RecoveryCodeForm({ pending, error, onSubmit, onCancel, alternative }: RecoveryCodeFormProps) {
  const [code, setCode] = useState("");
  const [incomplete, setIncomplete] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const ready = characterCount(code) === RECOVERY_CODE_CHARACTERS;
    setIncomplete(!ready);
    if (ready) onSubmit(code.trim());
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-5.5">
      <Field label={SIGN_IN_TEXT.recoveryLabel} error={incomplete ? SIGN_IN_TEXT.incompleteRecoveryCode : null}>
        {(control) => (
          <Input
            {...control}
            value={code}
            onChange={(event) => setCode(event.target.value)}
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            autoFocus
            disabled={pending}
            className="h-11 text-center tracking-wide tabular-nums"
          />
        )}
      </Field>
      {error && !incomplete ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={pending} className="w-full">
        {SIGN_IN_TEXT.verify}
      </Button>
      <div className="flex flex-col items-center gap-1">
        <QuietButton onClick={alternative.onSelect}>{alternative.label}</QuietButton>
        <QuietButton onClick={onCancel}>{SIGN_IN_TEXT.differentAccount}</QuietButton>
      </div>
    </form>
  );
}
