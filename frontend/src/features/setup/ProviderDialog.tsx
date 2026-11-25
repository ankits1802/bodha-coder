"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { addProvider, editProvider } from "@/lib/api/practice";
import type { Channel, Place, Provider, ProviderInput } from "@/lib/api/types";
import { ProviderFields } from "./ProviderFields";
import { draftFrom, inputFrom, validateProvider, type ProviderDraft, type ProviderErrors, type ProviderTextField } from "./providerForm";
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
  const [errors, setErrors] = useState<ProviderErrors>({});
  const save = useAction(saveProvider);
  const words = PROVIDER_TEXT.dialog;

  function change(field: ProviderTextField, value: string): void {
    setDraft((current) => ({ ...current, [field]: field === "channel" ? (value as Channel) : value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validateProvider(draft);
    setErrors(found);
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
      <form id={FORM_ID} noValidate onSubmit={submit} className="flex flex-col gap-4">
        <ProviderFields
          draft={draft}
          errors={errors}
          places={places}
          onChange={change}
          onActive={(active) => setDraft((current) => ({ ...current, active }))}
        />
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
