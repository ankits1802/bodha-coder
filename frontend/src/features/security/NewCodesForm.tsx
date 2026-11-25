"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { isSixDigitCode } from "@/lib/validation";
import { SECURITY_TEXT } from "./strings";

interface NewCodesFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (code: string) => Promise<boolean>;
}

export function NewCodesForm({ pending, error, onSubmit }: NewCodesFormProps) {
  const words = SECURITY_TEXT.recovery;
  const [code, setCode] = useState("");
  const [incomplete, setIncomplete] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const ready = isSixDigitCode(code);
    setIncomplete(!ready);
    if (ready && (await onSubmit(code))) setCode("");
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <Field label={words.code} error={incomplete ? words.incomplete : null} className="w-40">
          {(control) => (
            <Input
              {...control}
              value={code}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
              className="tabular-nums"
            />
          )}
        </Field>
        <Button type="submit" pending={pending}>
          {words.replace}
        </Button>
      </div>
      {error && !incomplete ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
    </form>
  );
}
