"use client";

import { useRef, useState } from "react";
import { CodeList } from "@/components/shared/CodeList";
import { KeyHint } from "@/components/shared/shortcuts/KeyHint";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { saveBilledCodes } from "@/lib/api/notes";
import type { NoteDetail, OverrideChoice } from "@/lib/api/types";
import { parseCodeList } from "@/lib/validation";
import { EMPTY_OVERRIDE, toOverride } from "../overrideReasons";
import { REVIEW_TEXT } from "../strings";
import { OverrideReasonPicker } from "./OverrideReasonPicker";

const words = REVIEW_TEXT.billed;

interface BilledCodesEditorProps {
  noteId: string;
  codes: string[];
  editable: boolean;
  editing: boolean;
  onEditing: (editing: boolean) => void;
  onSaved: (detail: NoteDetail) => void;
}

type BilledCodesFormProps = Omit<BilledCodesEditorProps, "editable" | "editing">;

function BilledCodesForm({ noteId, codes, onEditing, onSaved }: BilledCodesFormProps) {
  const form = useRef<HTMLFormElement>(null);
  const [draft, setDraft] = useState(codes.join(", "));
  const [reason, setReason] = useState(EMPTY_OVERRIDE);
  const [tried, setTried] = useState(false);
  const save = useAction((text: string, override: OverrideChoice) => saveBilledCodes(noteId, text, override));
  const invalid = parseCodeList(draft).invalid;
  const error = invalid.length > 0 ? words.invalid(invalid.join(", ")) : save.error;

  async function submit(): Promise<void> {
    setTried(true);
    const override = toOverride(reason);
    if (invalid.length > 0) return;
    if (!override) {
      form.current?.querySelector<HTMLInputElement>("input[type=radio]")?.focus();
      return;
    }
    const outcome = await save.run(draft, override);
    if (!outcome.ok) return;
    onEditing(false);
    onSaved(outcome.value);
  }

  return (
    <form
      ref={form}
      className="flex flex-wrap items-end gap-2 border-t border-hairline bg-footer-panel px-5 py-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <Field label={words.label} error={error} className="min-w-0 flex-[1_1_18rem]">
        {(control) => <Input {...control} autoFocus value={draft} onChange={(event) => setDraft(event.target.value)} className="tabular-nums" />}
      </Field>
      <div className="w-full">
        <OverrideReasonPicker
          label={REVIEW_TEXT.override.label(words.subject)}
          value={reason}
          showProblem={tried}
          onChange={setReason}
          onConfirm={() => void submit()}
          onCancel={() => onEditing(false)}
        />
      </div>
      <Button type="submit" size="sm" pending={save.pending} disabled={invalid.length > 0}>
        {words.save}
      </Button>
      <Button size="sm" variant="plain" onClick={() => onEditing(false)}>
        {words.cancel}
      </Button>
    </form>
  );
}

export function BilledCodesEditor({ editable, editing, ...form }: BilledCodesEditorProps) {
  if (editing && editable) return <BilledCodesForm {...form} />;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline bg-footer-panel px-5 py-4">
      <span className="flex flex-wrap items-center gap-2">
        <span className="text-subhead text-secondary">{words.label}</span>
        {form.codes.length > 0 ? <CodeList codes={form.codes} /> : <span className="text-subhead text-tertiary">{words.none}</span>}
      </span>
      {editable ? (
        <Button size="sm" onClick={() => form.onEditing(true)}>
          {words.edit} <KeyHint shortcut="editBilled" />
        </Button>
      ) : null}
    </div>
  );
}
