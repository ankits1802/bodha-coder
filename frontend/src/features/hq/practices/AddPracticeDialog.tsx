"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { addPractice } from "@/lib/api/hq";
import { PLAN_LABELS } from "@/lib/labels";
import { DEFAULT_TIME_ZONE, TIME_ZONES, TIME_ZONE_LABELS } from "@/lib/timeZones";
import { HQ_TEXT } from "../strings";
import { ChoiceField, TextField } from "./FormFields";
import {
  PLANS,
  newPracticeBody,
  validateNewPractice,
  type NewPracticeDraft,
  type NewPracticeErrors,
} from "./practiceForm";

const FORM_ID = "add-practice";
const BLANK: NewPracticeDraft = { name: "", admin_name: "", admin_email: "", plan: "trial", seats: "10", time_zone: DEFAULT_TIME_ZONE };

interface AddPracticeDialogProps {
  onClose: () => void;
  onAdded: () => void;
}

export function AddPracticeDialog({ onClose, onAdded }: AddPracticeDialogProps) {
  const [draft, setDraft] = useState<NewPracticeDraft>(BLANK);
  const [errors, setErrors] = useState<NewPracticeErrors>({});
  const add = useAction(addPractice);
  const words = HQ_TEXT.practices.form;
  const set = (field: keyof NewPracticeDraft) => (value: string) => setDraft((current) => ({ ...current, [field]: value }));

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validateNewPractice(draft);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const outcome = await add.run(newPracticeBody(draft));
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
          <Button type="submit" form={FORM_ID} variant="primary" pending={add.pending}>
            {words.add}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <TextField label={words.name} value={draft.name} error={errors.name} onChange={set("name")} className="sm:col-span-2" />
        <TextField label={words.adminName} value={draft.admin_name} error={errors.admin_name} onChange={set("admin_name")} />
        <TextField
          label={words.adminEmail}
          type="email"
          value={draft.admin_email}
          error={errors.admin_email}
          onChange={set("admin_email")}
        />
        <ChoiceField label={words.plan} value={draft.plan} options={PLANS} labels={PLAN_LABELS} onChange={set("plan")} />
        <TextField label={words.seats} type="number" min={1} inputMode="numeric" value={draft.seats} error={errors.seats} onChange={set("seats")} />
        <ChoiceField
          label={words.timeZone}
          value={draft.time_zone}
          options={TIME_ZONES}
          labels={TIME_ZONE_LABELS}
          onChange={set("time_zone")}
        />
        {add.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{add.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
