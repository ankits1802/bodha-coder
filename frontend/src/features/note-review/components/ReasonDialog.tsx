"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { TextArea } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";

export interface ReasonDialogText {
  title: string;
  reason: string;
  submit: string;
  cancel: string;
  invalid: string;
}

interface ReasonDialogProps {
  text: ReasonDialogText;
  minLength: number;
  onClose: () => void;
  onDone: () => void;
  submit: (reason: string) => Promise<unknown>;
}

export function ReasonDialog({ text, minLength, onClose, onDone, submit }: ReasonDialogProps) {
  const formId = useId();
  const [reason, setReason] = useState("");
  const [tried, setTried] = useState(false);
  const action = useAction(submit);
  const tooShort = reason.trim().length < minLength;

  async function onSubmit(): Promise<void> {
    setTried(true);
    if (tooShort) return;
    if ((await action.run(reason.trim())).ok) onDone();
  }

  const footer = (
    <>
      <Button onClick={onClose}>{text.cancel}</Button>
      <Button type="submit" form={formId} variant="primary" pending={action.pending}>
        {text.submit}
      </Button>
    </>
  );

  return (
    <Dialog open onClose={onClose} title={text.title} footer={footer}>
      <form
        id={formId}
        onSubmit={(event) => {
          event.preventDefault();
          void onSubmit();
        }}
      >
        <Field label={text.reason} error={tried && tooShort ? text.invalid : action.error}>
          {(control) => <TextArea {...control} value={reason} onChange={(event) => setReason(event.target.value)} rows={4} />}
        </Field>
      </form>
    </Dialog>
  );
}
