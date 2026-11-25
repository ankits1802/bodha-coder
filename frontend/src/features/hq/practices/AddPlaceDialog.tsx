"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { setHqPlace } from "@/lib/api/hq";
import { HQ_TEXT } from "../strings";
import { TextField } from "./FormFields";

const FORM_ID = "add-place";
const PLACE_CODE = /^\d{2}$/;

interface AddPlaceDialogProps {
  onClose: () => void;
  onAdded: () => void;
}

export function AddPlaceDialog({ onClose, onAdded }: AddPlaceDialogProps) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [checked, setChecked] = useState(false);
  const save = useAction(setHqPlace);
  const words = HQ_TEXT.places;
  const codeError = checked && !PLACE_CODE.test(code.trim()) ? words.errors.code : null;
  const nameError = checked && !name.trim() ? words.errors.name : null;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setChecked(true);
    if (!PLACE_CODE.test(code.trim()) || !name.trim()) return;
    const outcome = await save.run(code.trim(), name.trim(), true);
    if (outcome.ok) onAdded();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.addTitle}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={save.pending}>
            {words.save}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={submit} className="grid gap-4 sm:grid-cols-[8rem_1fr]">
        <TextField label={words.code} inputMode="numeric" maxLength={2} value={code} error={codeError} onChange={setCode} />
        <TextField label={words.name} value={name} error={nameError} onChange={setName} />
        {save.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{save.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
