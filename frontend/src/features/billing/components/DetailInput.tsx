import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { CLAIM_DETAILS_TEXT } from "../strings";

interface DetailInputProps {
  label: string;
  value: string;
  maxLength: number;
  onChange: (value: string) => void;
  error?: string;
  optional?: boolean;
  className?: string;
}

export function DetailInput({ label, value, maxLength, onChange, error, optional = false, className }: DetailInputProps) {
  return (
    <Field label={label} error={error} optional={optional ? CLAIM_DETAILS_TEXT.optional : undefined} className={className}>
      {(control) => (
        <Input {...control} maxLength={maxLength} autoComplete="off" value={value} onChange={(event) => onChange(event.target.value)} />
      )}
    </Field>
  );
}
