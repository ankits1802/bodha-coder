"use client";

import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Chevron } from "@/components/ui/Chevron";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { useCanSendTexts } from "@/hooks/useCanSendTexts";
import { addProvider, editProvider } from "@/lib/api/practice";
import type { Channel, PayerOption, Place, Provider, ProviderInput } from "@/lib/api/types";
import { CredentialFields } from "./CredentialFields";
import type { CredentialTextField } from "./credentialForm";
import { ProviderFields } from "./ProviderFields";
import { ProviderMoreFields } from "./ProviderMoreFields";
import {
  draftFrom,
  hidesError,
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
  payers: PayerOption[];
  onClose: () => void;
  onSaved: () => void;
}

function saveProvider(provider: Provider | null, input: ProviderInput): Promise<unknown> {
  return provider ? editProvider(provider.id, input) : addProvider(input);
}

export function ProviderDialog({ provider, places, payers, onClose, onSaved }: ProviderDialogProps) {
  const canSendTexts = useCanSendTexts();
  const moreId = useId();
  const [draft, setDraft] = useState<ProviderDraft>(() => draftFrom(provider, canSendTexts));
  const [touched, setTouched] = useState<string[]>([]);
  const [tried, setTried] = useState(false);
  const [more, setMore] = useState(false);
  const found = validateProvider(draft);
  const errors: ProviderErrors = tried ? found : touchedErrors(found, touched);
  const save = useAction(saveProvider);
  const words = PROVIDER_TEXT.dialog;
  const handlers = {
    draft,
    errors,
    onChange: (field: ProviderTextField, value: string) =>
      setDraft((current) => ({ ...current, [field]: field === "channel" ? (value as Channel) : value })),
    onTouched: (field: ProviderTextField) => setTouched((current) => (current.includes(field) ? current : [...current, field])),
  };

  function changeDetail(field: CredentialTextField, value: string): void {
    setDraft((current) => ({ ...current, details: { ...current.details, [field]: value } }));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTried(true);
    if (Object.keys(found).length > 0) {
      if (hidesError(found)) setMore(true);
      return;
    }
    const outcome = await save.run(provider, inputFrom(draft));
    if (outcome.ok) onSaved();
  }

  const footer = (
    <>
      <Button onClick={onClose}>{words.cancel}</Button>
      <Button type="submit" form={FORM_ID} variant="primary" pending={save.pending}>
        {words.save}
      </Button>
    </>
  );
  return (
    <Dialog open onClose={onClose} size="lg" title={provider ? words.editTitle : words.addTitle} footer={footer}>
      <form id={FORM_ID} noValidate onSubmit={submit} className="-m-1 flex max-h-[60svh] flex-col gap-4 overflow-y-auto p-1">
        <ProviderFields {...handlers} places={places} payers={payers} />
        <Button variant="plain" size="sm" className="-ml-3 self-start" aria-expanded={more} aria-controls={moreId} onClick={() => setMore((open) => !open)}>
          {words.more}
          <Chevron direction={more ? "down" : "right"} className="ml-1 flex-none text-secondary" />
        </Button>
        <div id={moreId} hidden={!more} className="flex flex-col gap-4">
          <ProviderMoreFields
            {...handlers}
            canSendTexts={canSendTexts}
            onActive={(active) => setDraft((current) => ({ ...current, active }))}
          />
          <CredentialFields
            draft={draft.details}
            errors={errors}
            onChange={changeDetail}
            onSignature={(onFile) => setDraft((current) => ({ ...current, details: { ...current.details, signature_on_file: onFile } }))}
          />
        </div>
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
