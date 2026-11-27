"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { CodeChip } from "@/components/ui/CodeChip";
import { Dialog } from "@/components/ui/Dialog";
import type { ClaimDiagnosis, PointerLine } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";

const WORDS = REVIEW_TEXT.pointers;
export const MAX_POINTERS = 4;

interface PointerEditorProps {
  line: PointerLine;
  diagnoses: ClaimDiagnosis[];
  pending: boolean;
  error: string | null;
  onSave: (pointers: string[]) => void;
  onClose: () => void;
}

export function toggledPointer(chosen: string[], code: string): string[] {
  if (chosen.includes(code)) return chosen.filter((item) => item !== code);
  return chosen.length < MAX_POINTERS ? [...chosen, code] : chosen;
}

function DiagnosisOption({ diagnosis, position, full, onToggle }: { diagnosis: ClaimDiagnosis; position: number; full: boolean; onToggle: () => void }) {
  const ordinal = WORDS.ordinals[position] ?? null;
  return (
    <label className="flex cursor-pointer items-center gap-3 border-b border-hairline py-2.5 last:border-b-0 has-disabled:cursor-not-allowed">
      <input
        type="checkbox"
        aria-label={WORDS.option(diagnosis.code, diagnosis.letter, ordinal)}
        checked={ordinal !== null}
        disabled={ordinal === null && full}
        onChange={onToggle}
        className="size-4.5 flex-none accent-label"
      />
      <span className="w-4 flex-none text-footnote text-secondary">{diagnosis.letter}</span>
      <CodeChip code={diagnosis.code} />
      <span className="ml-auto text-footnote text-secondary tabular-nums">{ordinal}</span>
    </label>
  );
}

export function PointerEditor({ line, diagnoses, pending, error, onSave, onClose }: PointerEditorProps) {
  const [chosen, setChosen] = useState<string[]>(line.pointers);
  const title = WORDS.title(line.label);
  const footer = (
    <>
      {line.stored ? (
        <Button variant="plain" className="mr-auto" onClick={() => onSave([])} disabled={pending}>
          {WORDS.useDefault}
        </Button>
      ) : null}
      <Button onClick={onClose}>{WORDS.cancel}</Button>
      <Button variant="primary" onClick={() => onSave(chosen)} pending={pending} disabled={chosen.length === 0}>
        {WORDS.save}
      </Button>
    </>
  );

  return (
    <Dialog open onClose={onClose} title={title} description={WORDS.chosen(chosen.length, MAX_POINTERS)} footer={footer}>
      <fieldset className="m-0 flex min-w-0 flex-col border-0 p-0">
        <legend className="sr-only">{title}</legend>
        {diagnoses.map((diagnosis) => (
          <DiagnosisOption
            key={diagnosis.code}
            diagnosis={diagnosis}
            position={chosen.indexOf(diagnosis.code)}
            full={chosen.length >= MAX_POINTERS}
            onToggle={() => setChosen((current) => toggledPointer(current, diagnosis.code))}
          />
        ))}
      </fieldset>
      {error ? (
        <p role="alert" className="m-0 text-footnote text-bad-text">
          {error}
        </p>
      ) : null}
    </Dialog>
  );
}
