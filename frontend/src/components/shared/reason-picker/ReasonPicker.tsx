"use client";

import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { SHARED_TEXT } from "../strings";
import { OTHER_REASON, REASON_NOTE_MAX, reasonAtKey, reasonProblem, type ReasonDraft } from "./reasonDraft";

const WORDS = SHARED_TEXT.reasons;
const PROBLEMS = { choose: WORDS.choose, note: WORDS.noteNeeded, long: WORDS.tooLong } as const;

export interface ReasonPickerProps<R extends string> {
  label: string;
  reasons: readonly R[];
  labels: Record<R, string>;
  value: ReasonDraft<R>;
  showProblem: boolean;
  autoFocus?: boolean;
  onChange: (draft: ReasonDraft<R>) => void;
  onConfirm?: () => void;
  onCancel?: () => void;
  children?: ReactNode;
}

function inNoteField(target: EventTarget): boolean {
  return target instanceof HTMLInputElement && target.type !== "radio";
}

export function ReasonPicker<R extends string>(props: ReasonPickerProps<R>) {
  const { label, reasons, labels, value, showProblem, autoFocus = false, onChange, onConfirm, onCancel, children } = props;
  const name = useId();
  const group = useRef<HTMLDivElement>(null);
  const problem = reasonProblem(value);

  useEffect(() => {
    if (!autoFocus) return;
    const radios = group.current?.querySelectorAll<HTMLInputElement>("input[type=radio]");
    const checked = Array.from(radios ?? []).find((radio) => radio.checked);
    (checked ?? radios?.[0])?.focus();
  }, [autoFocus]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    const picked = inNoteField(event.target) ? null : reasonAtKey(reasons, event.key);
    if (picked) {
      event.preventDefault();
      onChange({ ...value, reason: picked });
      group.current?.querySelector<HTMLInputElement>(`input[value="${picked}"]`)?.focus();
    } else if (event.key === "Enter" && onConfirm && !(event.target instanceof HTMLButtonElement)) {
      event.preventDefault();
      onConfirm();
    } else if (event.key === "Escape" && onCancel) {
      event.preventDefault();
      event.stopPropagation();
      onCancel();
    }
  }

  return (
    <div ref={group} role="group" aria-label={label} onKeyDown={onKeyDown} className="flex flex-col gap-3">
      <div role="radiogroup" aria-label={WORDS.reason} className="grid grid-cols-1 gap-x-4 gap-y-0.5 sm:grid-cols-2">
        {reasons.map((reason, index) => (
          <label key={reason} className="flex cursor-pointer items-center gap-2 rounded-control px-1.5 py-1 text-subhead hover:bg-row-hover">
            <input
              type="radio"
              name={name}
              value={reason}
              checked={value.reason === reason}
              onChange={() => onChange({ ...value, reason })}
              className="size-4 flex-none accent-label"
            />
            <kbd aria-hidden="true" className="inline-flex h-5 min-w-5 items-center justify-center rounded-control bg-chip px-1 font-sans text-caption font-semibold text-label">
              {index + 1}
            </kbd>
            <span>{labels[reason]}</span>
          </label>
        ))}
      </div>
      <Field label={WORDS.note} optional={value.reason === OTHER_REASON ? undefined : WORDS.optional} error={showProblem && problem ? PROBLEMS[problem] : null}>
        {(control) => (
          <Input {...control} maxLength={REASON_NOTE_MAX} value={value.note} onChange={(event) => onChange({ ...value, note: event.target.value })} />
        )}
      </Field>
      {children}
    </div>
  );
}
