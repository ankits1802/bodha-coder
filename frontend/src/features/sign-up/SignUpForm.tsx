"use client";

import type { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { requestSignup } from "@/lib/api/signup";
import type { SignUpOptions } from "@/lib/api/types";
import { preferredTimeZone } from "@/lib/timeZones";
import { AgreementField } from "./AgreementField";
import { DraftTextField, TimeZoneField } from "./DraftFields";
import { blankDraft, signupRequest, type SignUpField } from "./signUpDraft";
import { SIGN_UP_TEXT } from "./strings";
import { useSignUpDraft } from "./useSignUpDraft";

const FIELDS: readonly SignUpField[] = ["name", "practice_name", "email", "agreed"];

interface SignUpFormProps {
  options: SignUpOptions;
  onSent: (email: string) => void;
}

export function SignUpForm({ options, onSent }: SignUpFormProps) {
  const form = useSignUpDraft(blankDraft(preferredTimeZone()), FIELDS);
  const send = useAction(requestSignup);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!form.checkAll()) return;
    const body = signupRequest(form.draft);
    const outcome = await send.run(body);
    if (outcome.ok) onSent(body.email);
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-4">
      <DraftTextField form={form} field="name" label={SIGN_UP_TEXT.name} autoComplete="name" />
      <DraftTextField form={form} field="practice_name" label={SIGN_UP_TEXT.practiceName} autoComplete="organization" />
      <DraftTextField form={form} field="email" label={SIGN_UP_TEXT.email} type="email" autoComplete="email" />
      <TimeZoneField form={form} />
      <AgreementField form={form} options={options} />
      {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={send.pending} className="mt-1 w-full">
        {SIGN_UP_TEXT.create}
      </Button>
    </form>
  );
}
