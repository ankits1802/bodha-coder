"use client";

import type { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { completeIdentitySignup } from "@/lib/api/signup";
import type { LoginResult, PendingIdentity, SignUpOptions } from "@/lib/api/types";
import { preferredTimeZone } from "@/lib/timeZones";
import { AgreementField } from "./AgreementField";
import { DraftTextField, TimeZoneField } from "./DraftFields";
import { blankDraft, identitySignupRequest, type SignUpField } from "./signUpDraft";
import { SIGN_UP_TEXT } from "./strings";
import { useSignUpDraft } from "./useSignUpDraft";

const FIELDS: readonly SignUpField[] = ["name", "practice_name", "agreed"];

interface CompletionFormProps {
  identity: PendingIdentity;
  options: SignUpOptions;
  onCreated: (result: LoginResult) => void;
}

export function CompletionForm({ identity, options, onCreated }: CompletionFormProps) {
  const initial = blankDraft(preferredTimeZone(), { name: identity.name, email: identity.email });
  const form = useSignUpDraft(initial, FIELDS);
  const create = useAction(completeIdentitySignup);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!form.checkAll()) return;
    const outcome = await create.run(identitySignupRequest(form.draft));
    if (outcome.ok) onCreated(outcome.value);
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-0.5">
        <span className="text-subhead font-medium text-label">{SIGN_UP_TEXT.signedInAs}</span>
        <span className="text-body text-secondary">{identity.email}</span>
      </div>
      <DraftTextField form={form} field="name" label={SIGN_UP_TEXT.name} autoComplete="name" />
      <DraftTextField form={form} field="practice_name" label={SIGN_UP_TEXT.practiceName} autoComplete="organization" />
      <TimeZoneField form={form} />
      <AgreementField form={form} options={options} />
      {create.error ? <InlineAlert tone="bad">{create.error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={create.pending} className="mt-1 w-full">
        {SIGN_UP_TEXT.create}
      </Button>
    </form>
  );
}
