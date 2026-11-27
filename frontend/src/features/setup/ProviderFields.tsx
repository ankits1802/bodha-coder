import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Toggle } from "@/components/ui/Toggle";
import type { Channel, Place } from "@/lib/api/types";
import { CHANNEL_LABELS } from "@/lib/labels";
import type { ProviderDraft, ProviderErrors, ProviderTextField } from "./providerForm";
import { CREDENTIALS, PROVIDER_TEXT } from "./strings";

interface ProviderFieldsProps {
  draft: ProviderDraft;
  errors: ProviderErrors;
  places: Place[];
  onChange: (field: ProviderTextField, value: string) => void;
  onActive: (active: boolean) => void;
  onTouched: (field: ProviderTextField) => void;
}

const CHANNELS: readonly Channel[] = ["email", "sms"];

export function ProviderFields({ draft, errors, places, onChange, onActive, onTouched }: ProviderFieldsProps) {
  const words = PROVIDER_TEXT.dialog;
  const text = (field: ProviderTextField, label: string, type = "text", optional = true) => (
    <Field label={label} error={errors[field]} optional={optional ? words.optional : undefined}>
      {(control) => (
        <Input
          {...control}
          type={type}
          value={draft[field]}
          onChange={(event) => onChange(field, event.target.value)}
          onBlur={() => onTouched(field)}
        />
      )}
    </Field>
  );

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {text("name", words.name, "text", false)}
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
      {text("specialty", words.specialty)}
      {text("npi", words.npi)}
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
      <Field label={words.channel}>
        {(control) => (
          <Select
            {...control}
            value={draft.channel}
            options={CHANNELS.map((channel) => ({ value: channel, label: CHANNEL_LABELS[channel] }))}
            onChange={(value) => onChange("channel", value)}
          />
        )}
      </Field>
      {text("email", words.email, "email")}
      {text("phone", words.phone, "tel")}
      <div className="flex items-center justify-between gap-3 sm:col-span-2">
        <span aria-hidden="true" className="text-subhead font-medium">
          {words.active}
        </span>
        <Toggle label={words.active} checked={draft.active} onChange={onActive} />
      </div>
    </div>
  );
}
