"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input, TextArea } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { addPracticeMeasure, changePracticeMeasure } from "@/lib/api/practice";
import type { PracticeMeasure, PracticeMeasureInput } from "@/lib/api/types";
import { MEASURE_LIMITS, draftFrom, inputFrom, validateDraft, type MeasureDraft, type MeasureErrors } from "./practiceMeasureForm";
import { PRACTICE_MEASURE_TEXT } from "./strings";

const FORM_ID = "practice-measure-form";
const words = PRACTICE_MEASURE_TEXT.dialog;

interface PracticeMeasureDialogProps {
  measure: PracticeMeasure | null;
  onClose: () => void;
  onSaved: (measure: PracticeMeasure) => void;
}

interface DraftFieldProps {
  name: keyof MeasureDraft;
  label: string;
  draft: MeasureDraft;
  errors: MeasureErrors;
  onChange: (draft: MeasureDraft) => void;
  maxLength: number;
  long?: boolean;
  optional?: boolean;
  placeholder?: string;
}

function DraftField({ name, label, draft, errors, onChange, maxLength, long = false, optional = false, placeholder }: DraftFieldProps) {
  return (
    <Field label={label} error={errors[name]} optional={optional ? words.optional : undefined} className={long ? "sm:col-span-2" : ""}>
      {(control) =>
        long ? (
          <TextArea {...control} rows={3} maxLength={maxLength} value={draft[name]} onChange={(event) => onChange({ ...draft, [name]: event.target.value })} />
        ) : (
          <Input
            {...control}
            maxLength={maxLength}
            placeholder={placeholder}
            value={draft[name]}
            onChange={(event) => onChange({ ...draft, [name]: event.target.value })}
          />
        )
      }
    </Field>
  );
}

function saveMeasure(measure: PracticeMeasure | null, input: PracticeMeasureInput): Promise<PracticeMeasure> {
  return measure ? changePracticeMeasure(measure.key, input, measure.version) : addPracticeMeasure(input);
}

export function PracticeMeasureDialog({ measure, onClose, onSaved }: PracticeMeasureDialogProps) {
  const [draft, setDraft] = useState<MeasureDraft>(() => draftFrom(measure));
  const [errors, setErrors] = useState<MeasureErrors>({});
  const save = useAction(saveMeasure);
  const shared = { draft, errors, onChange: setDraft };
  const codeLength = (MEASURE_LIMITS.codesPerOutcome + 1) * 10;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validateDraft(draft);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const outcome = await save.run(measure, inputFrom(draft));
    if (outcome.ok) onSaved(outcome.value);
  }

  return (
    <Dialog
      open
      size="lg"
      onClose={onClose}
      title={measure ? words.editTitle : words.addTitle}
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
        <DraftField {...shared} name="name" label={words.name} maxLength={MEASURE_LIMITS.nameMax} />
        <DraftField {...shared} name="identifier" label={words.identifier} maxLength={MEASURE_LIMITS.identifierMax} optional />
        <DraftField {...shared} name="in_scope" label={words.inScope} maxLength={MEASURE_LIMITS.scopeMax} long />
        <DraftField {...shared} name="out_of_scope" label={words.outOfScope} maxLength={MEASURE_LIMITS.scopeMax} long optional />
        <DraftField {...shared} name="to_meet" label={words.toMeet} maxLength={MEASURE_LIMITS.toMeetMax} long />
        <DraftField {...shared} name="met_codes" label={words.metCodes} maxLength={codeLength} placeholder={words.codesPlaceholder} optional />
        <DraftField {...shared} name="not_met_codes" label={words.notMetCodes} maxLength={codeLength} placeholder={words.codesPlaceholder} optional />
        {save.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{save.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
