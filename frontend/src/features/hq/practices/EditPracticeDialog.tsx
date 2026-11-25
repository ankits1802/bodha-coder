"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { updatePractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { PLAN_LABELS, PRACTICE_STATUS_LABELS } from "@/lib/labels";
import { HQ_TEXT } from "../strings";
import { ChoiceField, TextField } from "./FormFields";
import { PLANS, STATUSES, editDraftFrom, practiceChanges, seatsError, zoneOptions, type PracticeEditDraft } from "./practiceForm";

const FORM_ID = "edit-practice";

interface EditPracticeDialogProps {
  practice: HqPractice;
  onClose: () => void;
  onSaved: () => void;
}

export function EditPracticeDialog({ practice, onClose, onSaved }: EditPracticeDialogProps) {
  const [draft, setDraft] = useState<PracticeEditDraft>(() => editDraftFrom(practice));
  const [checked, setChecked] = useState(false);
  const save = useAction(updatePractice);
  const words = HQ_TEXT.practices.form;
  const seats = checked ? seatsError(draft.seats) : null;
  const zones = zoneOptions(practice.time_zone);
  const set = (field: keyof PracticeEditDraft) => (value: string) => setDraft((current) => ({ ...current, [field]: value }));

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setChecked(true);
    if (seatsError(draft.seats)) return;
    const changes = practiceChanges(practice, draft);
    if (Object.keys(changes).length === 0) {
      onClose();
      return;
    }
    const outcome = await save.run(practice.id, changes);
    if (outcome.ok) onSaved();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.editTitle(practice.name)}
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
        <TextField label={words.name} value={draft.name} onChange={set("name")} />
        <ChoiceField
          label={words.status}
          value={draft.status}
          options={STATUSES}
          labels={PRACTICE_STATUS_LABELS}
          onChange={set("status")}
        />
        <ChoiceField label={words.plan} value={draft.plan} options={PLANS} labels={PLAN_LABELS} onChange={set("plan")} />
        <TextField label={words.seats} type="number" min={1} inputMode="numeric" value={draft.seats} error={seats} onChange={set("seats")} />
        <TextField label={words.renewsOn} type="date" value={draft.renews_on} onChange={set("renews_on")} />
        <ChoiceField
          label={words.timeZone}
          value={draft.time_zone}
          options={zones.options}
          labels={zones.labels}
          onChange={set("time_zone")}
        />
        {save.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{save.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
