"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import type { HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { confirmsDeletion } from "./practiceActions";

const FORM_ID = "delete-practice";

interface DeletePracticeDialogProps {
  practice: HqPractice;
  pending: boolean;
  error: string | null;
  onConfirm: (typedName: string) => void;
  onClose: () => void;
}

export function DeletePracticeDialog({ practice, pending, error, onConfirm, onClose }: DeletePracticeDialogProps) {
  const [typed, setTyped] = useState("");
  const words = HQ_TEXT.practices.confirm;
  const matches = confirmsDeletion(practice, typed);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (matches) onConfirm(typed.trim());
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.delete(practice.name)}
      description={words.deleteDescription}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button variant="danger" disabled={!matches} pending={pending} onClick={() => onConfirm(typed.trim())}>
            {words.deleteAction}
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
