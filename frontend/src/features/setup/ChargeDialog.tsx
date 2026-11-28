"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { setCharge } from "@/lib/api/clearinghouse";
import type { Charge, ChargeList } from "@/lib/api/types";
import { centsFrom, chargeCode, chargeDraftFrom, validateCharge, type ChargeDraft, type ChargeErrors } from "./chargeForm";
import { CHARGE_TEXT } from "./strings";

const FORM_ID = "charge-form";

interface ChargeDialogProps {
  charge: Charge | null;
  onClose: () => void;
  onSaved: (list: ChargeList) => void;
}

export function ChargeDialog({ charge, onClose, onSaved }: ChargeDialogProps) {
  const [draft, setDraft] = useState<ChargeDraft>(() => chargeDraftFrom(charge));
  const [errors, setErrors] = useState<ChargeErrors>({});
  const save = useAction(setCharge);
  const words = CHARGE_TEXT.dialog;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validateCharge(draft);
    setErrors(found);
    const cents = centsFrom(draft.amount);
    if (Object.keys(found).length > 0 || cents === null) return;
    const outcome = await save.run(chargeCode(draft), cents);
    if (outcome.ok) onSaved(outcome.value);
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={charge ? words.editTitle(charge.code) : words.addTitle}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={save.pending}>
            {words.save}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label={words.code} error={errors.code}>
          {(control) => (
            <Input
              {...control}
              maxLength={5}
              disabled={charge !== null}
              value={draft.code}
              onChange={(event) => setDraft({ ...draft, code: event.target.value })}
            />
          )}
        </Field>
        <Field label={words.amount} error={errors.amount}>
          {(control) => (
            <Input
              {...control}
              inputMode="decimal"
              value={draft.amount}
              onChange={(event) => setDraft({ ...draft, amount: event.target.value })}
              className="tabular-nums"
            />
          )}
        </Field>
        {save.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{save.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
