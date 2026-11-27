import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import type { Place } from "@/lib/api/types";
import { ProviderTextInput, type ProviderInputHandlers } from "./ProviderTextInput";
import { CREDENTIALS, PROVIDER_TEXT } from "./strings";

interface ProviderFieldsProps extends ProviderInputHandlers {
  places: Place[];
}

export function ProviderFields({ places, ...handlers }: ProviderFieldsProps) {
  const words = PROVIDER_TEXT.dialog;
  const { draft, onChange } = handlers;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <ProviderTextInput {...handlers} field="name" label={words.name} optional={false} />
      <Field label={words.credential}>
        {(control) => (
          <Select
            {...control}
            value={draft.credential}
            options={CREDENTIALS.map((credential) => ({ value: credential, label: credential }))}
            onChange={(value) => onChange("credential", value)}
          />
        )}
      </Field>
      <ProviderTextInput {...handlers} field="npi" label={words.npi} optional />
      <Field label={words.place} optional={words.optional}>
        {(control) => (
          <Select
            {...control}
            value={draft.place_code}
            options={[{ value: "", label: words.noPlace }, ...places.map((place) => ({ value: place.code, label: `${place.name} (${place.code})` }))]}
            onChange={(value) => onChange("place_code", value)}
          />
        )}
      </Field>
      <ProviderTextInput {...handlers} field="email" label={words.email} type="email" optional={draft.channel !== "email"} />
    </div>
  );
}
