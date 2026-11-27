"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { addProvider, editProvider } from "@/lib/api/practice";
import type { Channel, Place, Provider, ProviderInput } from "@/lib/api/types";
import { CredentialFields } from "./CredentialFields";
import type { CredentialTextField } from "./credentialForm";
import { ProviderFields } from "./ProviderFields";
import {
  draftFrom,
  inputFrom,
  touchedErrors,
  validateProvider,
  type ProviderDraft,
  type ProviderErrors,
  type ProviderTextField,
} from "./providerForm";
import { PROVIDER_TEXT } from "./strings";

const FORM_ID = "provider-form";

interface ProviderDialogProps {
  provider: Provider | null;
  places: Place[];
  onClose: () => void;
  onSaved: () => void;
}

function saveProvider(provider: Provider | null, input: ProviderInput): Promise<unknown> {
  return provider ? editProvider(provider.id, input) : addProvider(input);
}

export function ProviderDialog({ provider, places, onClose, onSaved }: ProviderDialogProps) {
  const [draft, setDraft] = useState<ProviderDraft>(() => draftFrom(provider));
  const [touched, setTouched] = useState<string[]>([]);
  const [tried, setTried] = useState(false);
  const found = validateProvider(draft);
  const errors: ProviderErrors = tried ? found : touchedErrors(found, touched);
  const save = useAction(saveProvider);
  const words = PROVIDER_TEXT.dialog;

  function change(field: ProviderTextField, value: string): void {
    setDraft((current) => ({ ...current, [field]: field === "channel" ? (value as Channel) : value }));
  }

  function changeDetail(field: CredentialTextField, value: string): void {
    setDraft((current) => ({ ...current, details: { ...current.details, [field]: value } }));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTried(true);
    if (Object.keys(found).length > 0) return;
    const outcome = await save.run(provider, inputFrom(draft));
    if (outcome.ok) onSaved();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={provider ? words.editTitle : words.addTitle}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={save.pending}>
            {words.save}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={submit} className="-m-1 flex max-h-[60svh] flex-col gap-4 overflow-y-auto p-1">
        <ProviderFields
          draft={draft}
          errors={errors}
          places={places}
          onChange={change}
          onActive={(active) => setDraft((current) => ({ ...current, active }))}
          onTouched={(field) => setTouched((current) => (current.includes(field) ? current : [...current, field]))}
        />
        <CredentialFields
          draft={draft.details}
          errors={errors}
          onChange={changeDetail}
          onSignature={(onFile) => setDraft((current) => ({ ...current, details: { ...current.details, signature_on_file: onFile } }))}
        />
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
