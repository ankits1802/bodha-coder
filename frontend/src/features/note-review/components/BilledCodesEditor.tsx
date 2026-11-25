"use client";

import { useState } from "react";
import { CodeList } from "@/components/shared/CodeList";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { saveBilledCodes } from "@/lib/api/notes";
import type { NoteDetail } from "@/lib/api/types";
import { parseCodeList } from "@/lib/validation";
import { REVIEW_TEXT } from "../strings";

interface BilledCodesEditorProps {
  noteId: string;
  codes: string[];
  editable: boolean;
  onSaved: (detail: NoteDetail) => void;
}

export function BilledCodesEditor({ noteId, codes, editable, onSaved }: BilledCodesEditorProps) {
  const words = REVIEW_TEXT.billed;
  const [draft, setDraft] = useState<string | null>(null);
  const save = useAction((text: string) => saveBilledCodes(noteId, text));
  const invalid = draft === null ? [] : parseCodeList(draft).invalid;
  const error = invalid.length > 0 ? words.invalid(invalid.join(", ")) : save.error;

  async function submit(): Promise<void> {
    if (draft === null || invalid.length > 0) return;
    const outcome = await save.run(draft);
    if (!outcome.ok) return;
    setDraft(null);
    onSaved(outcome.value);
  }

  if (draft === null) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline bg-footer-panel px-5 py-4">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-subhead text-secondary">{words.label}</span>
          {codes.length > 0 ? <CodeList codes={codes} /> : <span className="text-subhead text-tertiary">{words.none}</span>}
        </span>
        {editable ? (
          <Button size="sm" onClick={() => setDraft(codes.join(", "))}>
            {words.edit}
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <form
      className="flex flex-wrap items-end gap-2 border-t border-hairline bg-footer-panel px-5 py-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <Field label={words.label} error={error} className="min-w-0 flex-[1_1_18rem]">
        {(control) => <Input {...control} value={draft} onChange={(event) => setDraft(event.target.value)} className="tabular-nums" />}
      </Field>
      <Button type="submit" size="sm" pending={save.pending} disabled={invalid.length > 0}>
        {words.save}
      </Button>
      <Button size="sm" variant="plain" onClick={() => setDraft(null)}>
        {words.cancel}
      </Button>
    </form>
  );
}
