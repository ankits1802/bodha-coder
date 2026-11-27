import type { InputHTMLAttributes } from "react";
import { DatePicker } from "@/components/ui/DatePicker";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

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
      {(control) => <Select {...control} value={value} options={options.map((option) => ({ value: option, label: labels[option] }))} onChange={onChange} />}
    </Field>
  );
}

interface DayFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export function DayField({ label, value, onChange }: DayFieldProps) {
  return (
    <Field label={label}>
      {(control) => <DatePicker {...control} value={value || null} onChange={(day) => onChange(day ?? "")} />}
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
