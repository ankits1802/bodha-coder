"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input, Select } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { addPayer, changePayer } from "@/lib/api/practice";
import type { Payer, PayerInput, PlanType } from "@/lib/api/types";
import { PLAN_TYPES, payerDraftFrom, payerInputFrom, validatePayer, type PayerDraft, type PayerErrors } from "./payerForm";
import { PAYER_TEXT } from "./strings";

const FORM_ID = "payer-form";

interface PayerDialogProps {
  payer: Payer | null;
  onClose: () => void;
  onSaved: () => void;
}

function savePayer(payer: Payer | null, input: PayerInput): Promise<unknown> {
  return payer ? changePayer(payer.id, input) : addPayer(input);
}

export function PayerDialog({ payer, onClose, onSaved }: PayerDialogProps) {
  const [draft, setDraft] = useState<PayerDraft>(() => payerDraftFrom(payer));
  const [errors, setErrors] = useState<PayerErrors>({});
  const save = useAction(savePayer);
  const words = PAYER_TEXT.dialog;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validatePayer(draft);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const outcome = await save.run(payer, payerInputFrom(draft));
    if (outcome.ok) onSaved();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={payer ? words.editTitle : words.addTitle}
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
        <Field label={words.name} error={errors.name} className="sm:col-span-2">
          {(control) => (
            <Input {...control} maxLength={120} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
          )}
        </Field>
        <Field label={words.payerId} error={errors.payer_id} optional={words.optional}>
          {(control) => (
            <Input {...control} maxLength={15} value={draft.payer_id} onChange={(event) => setDraft({ ...draft, payer_id: event.target.value })} />
          )}
        </Field>
        <Field label={words.planType}>
          {(control) => (
            <Select {...control} value={draft.plan_type} onChange={(event) => setDraft({ ...draft, plan_type: event.target.value as PlanType })}>
              {PLAN_TYPES.map((type) => (
                <option key={type} value={type}>
                  {PAYER_TEXT.planTypes[type]}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <div className="flex items-center justify-between gap-3 sm:col-span-2">
          <span aria-hidden="true" className="text-subhead font-medium">
            {words.active}
          </span>
          <Toggle label={words.active} checked={draft.active} onChange={(active) => setDraft({ ...draft, active })} />
        </div>
        {save.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{save.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
