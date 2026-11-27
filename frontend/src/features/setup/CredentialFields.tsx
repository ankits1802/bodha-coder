import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Toggle } from "@/components/ui/Toggle";
import type { BillsUnder } from "@/lib/api/types";
import type { CredentialDraft, CredentialErrors, CredentialTextField } from "./credentialForm";
import { PROVIDER_TEXT } from "./strings";

interface CredentialFieldsProps {
  draft: CredentialDraft;
  errors: CredentialErrors;
  onChange: (field: CredentialTextField, value: string) => void;
  onSignature: (onFile: boolean) => void;
}

const BILLS_UNDER: readonly BillsUnder[] = ["individual", "group"];

export function CredentialFields({ draft, errors, onChange, onSignature }: CredentialFieldsProps) {
  const words = PROVIDER_TEXT.dialog.credentials;
  const optional = PROVIDER_TEXT.dialog.optional;
  const text = (field: CredentialTextField, label: string, extra: { maxLength?: number; inputMode?: "numeric" } = {}) => (
    <Field label={label} error={errors[field]} optional={optional}>
      {(control) => (
        <Input {...control} {...extra} value={draft[field]} autoComplete="off" onChange={(event) => onChange(field, event.target.value)} />
      )}
    </Field>
  );

  return (
    <fieldset className="m-0 grid gap-4 border-0 border-t border-hairline p-0 pt-4 sm:grid-cols-2">
      <legend className="float-left mb-1 text-subhead font-semibold sm:col-span-2">{words.title}</legend>
      {text("taxonomy_code", words.taxonomy, { maxLength: 10 })}
      {text("dea_number", words.dea, { maxLength: 9 })}
      {text("license_number", words.licenseNumber, { maxLength: 40 })}
      {text("license_state", words.licenseState, { maxLength: 2 })}
      <Field label={words.billsUnder} optional={optional}>
        {(control) => (
          <Select
            {...control}
            value={draft.bills_under}
            options={[{ value: "", label: words.billsUnderUnset }, ...BILLS_UNDER.map((choice) => ({ value: choice, label: words.billsUnderLabels[choice] }))]}
            onChange={(value) => onChange("bills_under", value)}
          />
        )}
      </Field>
      {text("group_npi", words.groupNpi, { maxLength: 10, inputMode: "numeric" })}
      {text("supervising_physician", words.supervising, { maxLength: 120 })}
      <div className="flex items-center justify-between gap-3 self-end sm:min-h-9">
        <span aria-hidden="true" className="text-subhead font-medium">
          {words.signature}
        </span>
        <Toggle label={words.signature} checked={draft.signature_on_file} onChange={onSignature} />
      </div>
    </fieldset>
  );
}
