import type { InputHTMLAttributes } from "react";
import { Field } from "@/components/ui/Field";
import { Input, Select } from "@/components/ui/Input";

interface ChoiceFieldProps<V extends string> {
  label: string;
  value: V;
  options: readonly V[];
  labels: Record<V, string>;
  onChange: (value: V) => void;
}

export function ChoiceField<V extends string>({ label, value, options, labels, onChange }: ChoiceFieldProps<V>) {
  return (
    <Field label={label}>
      {(control) => (
        <Select {...control} value={value} onChange={(event) => onChange(event.target.value as V)}>
          {options.map((option) => (
            <option key={option} value={option}>
              {labels[option]}
            </option>
          ))}
        </Select>
      )}
    </Field>
  );
}

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value"> {
  label: string;
  value: string;
  error?: string | null;
  onChange: (value: string) => void;
}

export function TextField({ label, value, error, onChange, className, ...rest }: TextFieldProps) {
  return (
    <Field label={label} error={error} className={className}>
      {(control) => <Input {...control} {...rest} value={value} onChange={(event) => onChange(event.target.value)} />}
    </Field>
  );
}
