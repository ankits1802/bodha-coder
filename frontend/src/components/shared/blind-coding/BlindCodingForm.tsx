"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import type { BlindAnswer } from "@/lib/api/types";
import { EMPTY_DRAFT, parseAnswer, type AnswerDraft, type AnswerErrors, type AnswerField } from "./answerDraft";
import { BLIND_TEXT } from "./strings";

interface BlindCodingFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (answer: BlindAnswer) => void;
}

const FIELDS: { field: AnswerField; label: string; optional: boolean }[] = [
  { field: "em", label: BLIND_TEXT.emLabel, optional: false },
  { field: "icd", label: BLIND_TEXT.icdLabel, optional: false },
  { field: "modifiers", label: BLIND_TEXT.modifiersLabel, optional: true },
];

export function BlindCodingForm({ pending, error, onSubmit }: BlindCodingFormProps) {
  const [draft, setDraft] = useState<AnswerDraft>(EMPTY_DRAFT);
  const [errors, setErrors] = useState<AnswerErrors>({});

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const parsed = parseAnswer(draft);
    if (!parsed.ok) {
      setErrors(parsed.errors);
      return;
    }
    setErrors({});
    onSubmit(parsed.answer);
  }

  return (
    <form aria-label={BLIND_TEXT.formLabel} onSubmit={submit} noValidate className="flex flex-col gap-4">
      {FIELDS.map(({ field, label, optional }) => (
        <Field key={field} label={label} error={errors[field]} optional={optional ? BLIND_TEXT.optional : undefined}>
          {(control) => (
            <Input
              {...control}
              autoFocus={field === "em"}
              autoComplete="off"
              spellCheck={false}
              className="tabular-nums uppercase"
              value={draft[field]}
              onChange={(event) => setDraft((current) => ({ ...current, [field]: event.target.value }))}
            />
          )}
        </Field>
      ))}
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button type="submit" variant="primary" pending={pending} className="self-start">
        {BLIND_TEXT.submit}
      </Button>
    </form>
  );
}
