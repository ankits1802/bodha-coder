"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { DatePicker } from "@/components/ui/DatePicker";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { RadioOption } from "@/components/ui/RadioOption";
import { useAction } from "@/hooks/useAction";
import { renewPractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { addDays } from "@/lib/dates";
import { formatCalendarDay } from "@/lib/format";
import { HQ_TEXT } from "../strings";
import { canRenew, choosePreset, practiceToday, RENEWAL_PRESETS, renewalBase, type RenewalChoice } from "./renewal";

const FORM_ID = "renew-practice";

interface RenewDialogProps {
  practice: HqPractice;
  onDone: (notice: string) => void;
  onClose: () => void;
}

export function RenewDialog({ practice, onDone, onClose }: RenewDialogProps) {
  const words = HQ_TEXT.practices.renewal;
  const today = practiceToday(practice);
  const base = renewalBase(practice, today);
  const [choice, setChoice] = useState<RenewalChoice>(() => choosePreset("year1", base));
  const renew = useAction(renewPractice);
  const ready = canRenew(choice, today);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!ready) return;
    const until = choice.preset === "noEnd" ? null : choice.until;
    const outcome = await renew.run(practice.id, until);
    if (!outcome.ok) return;
    const ends = outcome.value.renews_on;
    onDone(ends ? words.renewed(practice.name, formatCalendarDay(ends, "year")) : words.renewedNoEnd(practice.name));
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.title(practice.name)}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={!ready} pending={renew.pending}>
            {words.action}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
        <fieldset className="m-0 grid grid-cols-2 gap-2 border-0 p-0 sm:grid-cols-3">
          <legend className="mb-2 text-callout font-medium text-label">{words.length}</legend>
          {RENEWAL_PRESETS.map((preset) => (
            <RadioOption
              key={preset}
              name="renewal-preset"
              value={preset}
              checked={choice.preset === preset}
              onSelect={() => setChoice(choosePreset(preset, base))}
            >
              {words.presets[preset]}
            </RadioOption>
          ))}
        </fieldset>
        <Field label={words.until}>
          {(control) => (
            <DatePicker
              {...control}
              value={choice.preset === "noEnd" ? null : choice.until}
              min={addDays(today, 1) ?? undefined}
              today={today}
              disabled={choice.preset === "noEnd"}
              onChange={(until) => setChoice({ preset: null, until })}
            />
          )}
        </Field>
        <p className="m-0 text-callout text-secondary" aria-live="polite">
          {choice.preset === "noEnd" || !choice.until ? words.noEnd : words.ends(formatCalendarDay(choice.until, "year"))}
        </p>
        {renew.error ? <InlineAlert tone="bad">{renew.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
