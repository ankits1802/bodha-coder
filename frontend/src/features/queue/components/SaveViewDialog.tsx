"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { QUEUE_TEXT } from "../strings";

const FORM_ID = "save-queue-view";
const NAME_LIMIT = 60;

interface SaveViewDialogProps {
  open: boolean;
  pending: boolean;
  error: string | null;
  onSave: (name: string) => void;
  onClose: () => void;
}

export function SaveViewDialog({ open, pending, error, onSave, onClose }: SaveViewDialogProps) {
  const words = QUEUE_TEXT.views;
  const [name, setName] = useState("");
  const trimmed = name.trim();

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (trimmed) onSave(trimmed);
  }

  const footer = (
    <>
      <Button onClick={onClose}>{QUEUE_TEXT.cancel}</Button>
      <Button type="submit" form={FORM_ID} variant="primary" disabled={!trimmed} pending={pending}>
        {words.saveConfirm}
      </Button>
    </>
  );
  return (
    <Dialog open={open} onClose={onClose} title={words.saveTitle} footer={footer}>
      <form id={FORM_ID} onSubmit={submit} className="flex flex-col gap-4">
        <Field label={words.name}>
          {(control) => <Input {...control} autoFocus maxLength={NAME_LIMIT} value={name} onChange={(event) => setName(event.target.value)} />}
        </Field>
        {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
