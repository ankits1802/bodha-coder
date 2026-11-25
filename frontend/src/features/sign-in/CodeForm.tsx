"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { CODE_LENGTH, CodeInput } from "@/components/shared/CodeInput";
import { isSixDigitCode } from "@/lib/validation";
import { QuietButton } from "./QuietButton";
import { SIGN_IN_TEXT } from "./strings";

export interface Alternative {
  label: string;
  onSelect: () => void;
}

interface CodeFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (code: string) => void;
  onCancel: () => void;
  alternative?: Alternative;
}

export function CodeForm({ pending, error, onSubmit, onCancel, alternative }: CodeFormProps) {
  const [code, setCode] = useState("");
  const [incomplete, setIncomplete] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const ready = code.length === CODE_LENGTH && isSixDigitCode(code);
    setIncomplete(!ready);
    if (ready) onSubmit(code);
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-5.5">
      <CodeInput
        value={code}
        onChange={setCode}
        label={SIGN_IN_TEXT.codeLabel}
        digitLabel={SIGN_IN_TEXT.digitLabel}
        disabled={pending}
        autoFocus
      />
      {incomplete ? <InlineAlert tone="bad">{SIGN_IN_TEXT.incompleteCode}</InlineAlert> : null}
      {error && !incomplete ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={pending} className="w-full">
        {SIGN_IN_TEXT.verify}
      </Button>
      <div className="flex flex-col items-center gap-1">
        {alternative ? <QuietButton onClick={alternative.onSelect}>{alternative.label}</QuietButton> : null}
        <QuietButton onClick={onCancel}>{SIGN_IN_TEXT.differentAccount}</QuietButton>
      </div>
    </form>
  );
}
