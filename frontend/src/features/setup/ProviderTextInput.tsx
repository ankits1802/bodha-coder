import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import type { ProviderDraft, ProviderErrors, ProviderTextField } from "./providerForm";
import { PROVIDER_TEXT } from "./strings";

export interface ProviderInputHandlers {
  draft: ProviderDraft;
  errors: ProviderErrors;
  onChange: (field: ProviderTextField, value: string) => void;
  onTouched: (field: ProviderTextField) => void;
}

interface ProviderTextInputProps extends ProviderInputHandlers {
  field: ProviderTextField;
  label: string;
  type?: "text" | "email" | "tel";
  optional: boolean;
}

export function ProviderTextInput({ field, label, type = "text", optional, draft, errors, onChange, onTouched }: ProviderTextInputProps) {
  return (
    <Field label={label} error={errors[field]} optional={optional ? PROVIDER_TEXT.dialog.optional : undefined}>
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
}
