import type { HTMLInputTypeAttribute } from "react";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TIME_ZONES, TIME_ZONE_LABELS } from "@/lib/timeZones";
import { SIGN_UP_TEXT } from "./strings";
import type { DraftForm } from "./useSignUpDraft";

type TextField = "name" | "practice_name" | "email";

interface DraftTextFieldProps {
  form: DraftForm;
  field: TextField;
  label: string;
  type?: HTMLInputTypeAttribute;
  autoComplete: string;
}

export function DraftTextField({ form, field, label, type = "text", autoComplete }: DraftTextFieldProps) {
  return (
    <Field label={label} error={form.errors[field]}>
      {(control) => (
        <Input
          {...control}
          type={type}
          autoComplete={autoComplete}
          value={form.draft[field]}
          onChange={(event) => form.change(field, event.target.value)}
          onBlur={() => form.touch(field)}
        />
      )}
    </Field>
  );
}

export function TimeZoneField({ form }: { form: DraftForm }) {
  return (
    <Field label={SIGN_UP_TEXT.timeZone}>
      {(control) => (
        <Select
          {...control}
          value={form.draft.time_zone}
          options={TIME_ZONES.map((zone) => ({ value: zone, label: TIME_ZONE_LABELS[zone] ?? zone }))}
          onChange={(value) => form.change("time_zone", value)}
        />
      )}
    </Field>
  );
}
