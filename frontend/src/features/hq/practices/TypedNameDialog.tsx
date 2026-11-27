"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { HQ_TEXT } from "../strings";
import { confirmsName, type TypedActionKind } from "./practiceActions";

const FORM_ID = "typed-practice-action";
const words = HQ_TEXT.practices.confirm;

export interface TypedActionWords {
  title: (name: string) => string;
  description: string;
  action: string;
}

const KIND_WORDS: Record<TypedActionKind, TypedActionWords> = {
  close: { title: words.close, description: words.closeDescription, action: words.closeAction },
  purge: { title: words.purge, description: words.purgeDescription, action: words.purgeAction },
};

interface TypedNameDialogProps {
  kind: TypedActionKind;
  subject: { name: string };
  kindWords?: Record<TypedActionKind, TypedActionWords>;
  pending: boolean;
  error: string | null;
  onConfirm: (typedName: string) => void;
  onClose: () => void;
}

export function TypedNameDialog({ kind, subject, kindWords = KIND_WORDS, pending, error, onConfirm, onClose }: TypedNameDialogProps) {
  const [typed, setTyped] = useState("");
  const text = kindWords[kind];
  const matches = confirmsName(subject, typed);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (matches) onConfirm(typed.trim());
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={text.title(subject.name)}
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
        <Field label={words.typeName(subject.name)}>
          {(control) => (
            <Input {...control} value={typed} autoComplete="off" spellCheck={false} onChange={(event) => setTyped(event.target.value)} />
          )}
        </Field>
        {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
