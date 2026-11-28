"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { DatePicker } from "@/components/ui/DatePicker";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input, TextArea } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { saveEhrConnection } from "@/lib/api/ehrConnection";
import type { EhrConnection } from "@/lib/api/types";
import { NOTE_TYPES, draftFrom, hasProblems, problemsOf, settingsFrom, withNoteType, type EhrDraft } from "./ehrForm";
import { EHR_TEXT } from "./strings";

interface EhrSettingsFormProps {
  view: EhrConnection;
  today: string;
  onSaved: (view: EhrConnection) => void;
}

const words = EHR_TEXT;

export function EhrSettingsForm({ view, today, onSaved }: EhrSettingsFormProps) {
  const [draft, setDraft] = useState<EhrDraft>(() => draftFrom(view));
  const [saved, setSaved] = useState(false);
  const [touched, setTouched] = useState(false);
  const save = useAction(saveEhrConnection);
  const problems = problemsOf(draft);
  const shown = touched ? problems : null;

  function change(next: Partial<EhrDraft>): void {
    setSaved(false);
    setDraft((current) => ({ ...current, ...next }));
  }

  async function submit(): Promise<void> {
    setTouched(true);
    if (hasProblems(problems)) return;
    const outcome = await save.run(settingsFrom(draft));
    if (!outcome.ok) return;
    setDraft(draftFrom(outcome.value));
    setSaved(true);
    onSaved(outcome.value);
  }

  return (
    <div className="flex flex-col gap-4 border-t border-hairline px-4 py-4">
      <span className="text-subhead font-medium text-label">{words.settings}</span>
      <Field label={words.baseUrl} error={shown?.baseUrl}>
        {(control) => (
          <Input {...control} type="url" inputMode="url" autoComplete="off" spellCheck={false} value={draft.baseUrl} onChange={(event) => change({ baseUrl: event.target.value })} />
        )}
      </Field>
      {view.connection ? (
        <div className="flex flex-col gap-1.5">
          <span className="text-subhead font-medium text-label">{words.tokenEndpoint}</span>
          <span className="text-body break-all text-secondary">{view.connection.token_endpoint}</span>
        </div>
      ) : null}
      <Field label={words.clientId} error={shown?.clientId}>
        {(control) => (
          <Input {...control} autoComplete="off" spellCheck={false} value={draft.clientId} onChange={(event) => change({ clientId: event.target.value })} />
        )}
      </Field>
      <Field label={words.scopes} error={shown?.scopes}>
        {(control) => <TextArea {...control} rows={4} spellCheck={false} value={draft.scopes} onChange={(event) => change({ scopes: event.target.value })} />}
      </Field>
      <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
        <legend className="mb-1.5 text-subhead font-medium text-label">{words.noteTypes}</legend>
        {NOTE_TYPES.map((type) => (
          <div key={type} className="flex h-10 items-center justify-between gap-3 text-body">
            <span>{words.noteTypeNames[type]}</span>
            <Toggle
              label={words.noteTypeNames[type]}
              checked={draft.noteTypes.includes(type)}
              onChange={(chosen) => change({ noteTypes: withNoteType(draft, type, chosen) })}
            />
          </div>
        ))}
        {shown?.noteTypes ? <span className="text-footnote text-bad-text">{shown.noteTypes}</span> : null}
      </fieldset>
      <Field label={words.startDate} error={shown?.startDate} className="max-w-60">
        {(control) => <DatePicker {...control} value={draft.startDate} max={today} today={today} onChange={(startDate) => change({ startDate })} />}
      </Field>
      <div className="flex flex-wrap items-center justify-end gap-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {saved ? (
          <span role="status" className="text-subhead text-secondary">
            {words.saved}
          </span>
        ) : null}
        <Button pending={save.pending} onClick={() => void submit()}>
          {words.save}
        </Button>
      </div>
    </div>
  );
}
