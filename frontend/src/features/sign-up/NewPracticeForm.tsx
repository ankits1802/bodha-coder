"use client";

import type { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { startPractice } from "@/lib/api/auth";
import type { SignUpOptions } from "@/lib/api/types";
import { enterPractice } from "@/lib/session/practiceEntry";
import { preferredTimeZone } from "@/lib/timeZones";
import { AgreementField } from "./AgreementField";
import { DraftTextField, TimeZoneField } from "./DraftFields";
import { blankDraft, newPracticeRequest, type SignUpField } from "./signUpDraft";
import { SIGN_UP_TEXT } from "./strings";
import { useSignUpDraft } from "./useSignUpDraft";

const FIELDS: readonly SignUpField[] = ["practice_name", "agreed"];

export function NewPracticeForm({ options }: { options: SignUpOptions }) {
  const form = useSignUpDraft(blankDraft(preferredTimeZone()), FIELDS);
  const start = useAction(startPractice);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!form.checkAll()) return;
    const outcome = await start.run(newPracticeRequest(form.draft));
    if (outcome.ok) enterPractice(outcome.value);
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-4">
      <DraftTextField form={form} field="practice_name" label={SIGN_UP_TEXT.practiceName} autoComplete="organization" />
      <TimeZoneField form={form} />
      <AgreementField form={form} options={options} />
      {start.error ? <InlineAlert tone="bad">{start.error}</InlineAlert> : null}
      <Button type="submit" variant="primary" pending={start.pending} className="self-start">
        {SIGN_UP_TEXT.create}
      </Button>
    </form>
  );
}
