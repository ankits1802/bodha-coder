"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { DateRange } from "@/components/ui/DateRange";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { RemoteView } from "@/components/ui/RemoteView";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { useRemote } from "@/hooks/useRemote";
import { assignTraining, getQualityOptions } from "@/lib/api/quality";
import type { QualityOptions } from "@/lib/api/types";
import { firstTrainingDraft, trainingInput, type TrainingDraft } from "../trainingDraft";
import { TRAINING_TEXT } from "../strings";

const FORM_ID = "assign-training-form";
const REMOTE_TEXT = { loading: TRAINING_TEXT.loading, empty: TRAINING_TEXT.noAssigned, retry: TRAINING_TEXT.retry };

interface FieldsProps {
  draft: TrainingDraft;
  options: QualityOptions;
  onChange: (draft: TrainingDraft) => void;
}

function TrainingFields({ draft, options, onChange }: FieldsProps) {
  const words = TRAINING_TEXT.dialog;
  const set = (changes: Partial<TrainingDraft>) => onChange({ ...draft, ...changes });
  return (
    <>
      <Field label={words.trainee}>
        {(control) => (
          <Select
            {...control}
            value={draft.traineeId}
            options={[{ value: "", label: words.choose }, ...options.reviewers.map((person) => ({ value: person.id, label: person.name }))]}
            onChange={(traineeId) => set({ traineeId })}
          />
        )}
      </Field>
      <Field label={words.provider}>
        {(control) => (
          <Select
            {...control}
            value={draft.providerId}
            options={[{ value: "", label: words.anyProvider }, ...options.providers.map((provider) => ({ value: provider.id, label: provider.name }))]}
            onChange={(providerId) => set({ providerId })}
          />
        )}
      </Field>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <DateRange
          start={draft.start || null}
          end={draft.end || null}
          labels={{ start: words.start, end: words.end }}
          onChange={(range) => set({ start: range.start ?? "", end: range.end ?? "" })}
        />
        <Field label={words.size}>
          {(control) => <Input {...control} inputMode="numeric" value={draft.size} onChange={(event) => set({ size: event.target.value.trim() })} />}
        </Field>
      </div>
    </>
  );
}

export function AssignTrainingDialog({ onClose, onAssigned }: { onClose: () => void; onAssigned: () => void }) {
  const today = usePracticeToday();
  const options = useRemote("training-options", getQualityOptions);
  const [draft, setDraft] = useState<TrainingDraft>(() => firstTrainingDraft(today));
  const assign = useAction(assignTraining);
  const input = trainingInput(draft);
  const words = TRAINING_TEXT.dialog;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (input && (await assign.run(input)).ok) onAssigned();
  }

  const footer = (
    <>
      <Button onClick={onClose} disabled={assign.pending}>
        {words.cancel}
      </Button>
      <Button type="submit" form={FORM_ID} variant="primary" pending={assign.pending} disabled={!input}>
        {words.submit}
      </Button>
    </>
  );
  return (
    <Dialog open onClose={onClose} title={words.title} footer={footer}>
      <RemoteView state={options.state} text={REMOTE_TEXT} isEmpty={(data) => data.reviewers.length === 0} onRetry={options.reload}>
        {(data) => (
          <form id={FORM_ID} onSubmit={(event) => void submit(event)} className="flex flex-col gap-5">
            <TrainingFields draft={draft} options={data} onChange={setDraft} />
            {assign.error ? <InlineAlert tone="bad">{assign.error}</InlineAlert> : null}
          </form>
        )}
      </RemoteView>
    </Dialog>
  );
}
