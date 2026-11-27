"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import type { HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { confirmsName, type TypedActionKind } from "./practiceActions";

const FORM_ID = "typed-practice-action";
const words = HQ_TEXT.practices.confirm;
const KIND_WORDS: Record<TypedActionKind, { title: (name: string) => string; description: string; action: string }> = {
  close: { title: words.close, description: words.closeDescription, action: words.closeAction },
  purge: { title: words.purge, description: words.purgeDescription, action: words.purgeAction },
};

interface TypedNameDialogProps {
  kind: TypedActionKind;
  practice: HqPractice;
  pending: boolean;
  error: string | null;
  onConfirm: (typedName: string) => void;
  onClose: () => void;
}

export function TypedNameDialog({ kind, practice, pending, error, onConfirm, onClose }: TypedNameDialogProps) {
  const [typed, setTyped] = useState("");
  const text = KIND_WORDS[kind];
  const matches = confirmsName(practice, typed);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (matches) onConfirm(typed.trim());
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={text.title(practice.name)}
      description={text.description}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button variant="danger" disabled={!matches} pending={pending} onClick={() => onConfirm(typed.trim())}>
            {text.action}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={submit} className="flex flex-col gap-4">
        <Field label={words.typeName(practice.name)}>
          {(control) => (
            <Input {...control} value={typed} autoComplete="off" spellCheck={false} onChange={(event) => setTyped(event.target.value)} />
          )}
        </Field>
        {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
