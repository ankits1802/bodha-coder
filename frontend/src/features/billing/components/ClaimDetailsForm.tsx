"use client";

import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { saveClaimDetails } from "@/lib/api/claims";
import { setNotePayer } from "@/lib/api/notes";
import type { BillingRow, ClaimDetailsInput, ClaimDetailsView, PayerOption } from "@/lib/api/types";
import { detailsDraftFrom, detailsInputFrom, readName, validateDetails, type DetailsDraft, type DetailsErrors } from "../claimDetailsModel";
import { missingLabel } from "../claimStatus";
import { CLAIM_DETAILS_TEXT } from "../strings";
import { CoverageFields } from "./CoverageFields";
import { PatientFields } from "./PatientFields";

interface ClaimDetailsFormProps {
  row: BillingRow;
  view: ClaimDetailsView;
  payers: PayerOption[];
  onClose: () => void;
  onSaved: () => void;
}

async function persist(noteId: string, payer: string, details: ClaimDetailsInput): Promise<ClaimDetailsView> {
  if (payer) await setNotePayer(noteId, payer);
  return saveClaimDetails(noteId, details);
}

export function ClaimDetailsForm({ row, view, payers, onClose, onSaved }: ClaimDetailsFormProps) {
  const [draft, setDraft] = useState<DetailsDraft>(() => detailsDraftFrom(view));
  const [errors, setErrors] = useState<DetailsErrors>({});
  const save = useAction(persist);
  const formId = useId();
  const words = CLAIM_DETAILS_TEXT;
  const missing = row.claim?.missing ?? [];
  const needsPayer = missing.includes("payer");
  const name = readName(view);
  const change = (part: Partial<DetailsDraft>) => setDraft((current) => ({ ...current, ...part }));

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validateDetails(draft, needsPayer);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const outcome = await save.run(row.id, needsPayer ? draft.payer : "", detailsInputFrom(draft));
    if (outcome.ok) onSaved();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={words.title}
      description={name ? words.readName(name) : (row.patient_name ?? undefined)}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={formId} variant="primary" pending={save.pending}>
            {words.save}
          </Button>
        </>
      }
    >
      <form id={formId} noValidate onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {missing.length > 0 ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="warn">{`${words.missingLabel}: ${missing.map(missingLabel).join(", ")}`}</InlineAlert>
          </div>
        ) : null}
        {needsPayer ? (
          <Field label={words.payer} error={errors.payer} className="sm:col-span-2">
            {(control) => (
              <Select
                {...control}
                value={draft.payer}
                options={[{ value: "", label: words.noPayer }, ...payers.map((payer) => ({ value: payer.id, label: payer.name }))]}
                onChange={(payer) => change({ payer })}
              />
            )}
          </Field>
        ) : null}
        <PatientFields draft={draft} errors={errors} serviceDate={row.service_date} onChange={change} />
        <CoverageFields draft={draft} errors={errors} onChange={change} />
        {save.error ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="bad">{save.error}</InlineAlert>
          </div>
        ) : null}
      </form>
    </Dialog>
  );
}
