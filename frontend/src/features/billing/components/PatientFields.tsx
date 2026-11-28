import { DatePicker } from "@/components/ui/DatePicker";
import { Field } from "@/components/ui/Field";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { PatientSex } from "@/lib/api/types";
import { SEXES, type DetailsChange, type DetailsDraft, type DetailsErrors } from "../claimDetailsModel";
import { CLAIM_DETAILS_TEXT } from "../strings";
import { DetailInput } from "./DetailInput";

interface PatientFieldsProps {
  draft: DetailsDraft;
  errors: DetailsErrors;
  serviceDate: string;
  onChange: DetailsChange;
}

export function PatientFields({ draft, errors, serviceDate, onChange }: PatientFieldsProps) {
  const words = CLAIM_DETAILS_TEXT;
  return (
    <>
      <DetailInput
        label={words.patientLast}
        value={draft.patient_last}
        maxLength={60}
        error={errors.patient_last}
        onChange={(patient_last) => onChange({ patient_last })}
      />
      <DetailInput
        label={words.patientFirst}
        value={draft.patient_first}
        maxLength={35}
        error={errors.patient_first}
        onChange={(patient_first) => onChange({ patient_first })}
      />
      <Field label={words.birthDate} error={errors.patient_birth_date}>
        {(control) => (
          <DatePicker {...control} value={draft.patient_birth_date} max={serviceDate} onChange={(patient_birth_date) => onChange({ patient_birth_date })} />
        )}
      </Field>
      <div className="flex flex-col gap-1.5">
        <span aria-hidden="true" className="text-subhead font-medium text-label">
          {words.sex}
        </span>
        <SegmentedControl<PatientSex>
          label={words.sex}
          value={draft.patient_sex}
          segments={SEXES.map((value) => ({ value, label: words.sexes[value] }))}
          onChange={(patient_sex) => onChange({ patient_sex })}
        />
        {errors.patient_sex ? <span className="text-footnote text-bad-text">{errors.patient_sex}</span> : null}
      </div>
      <DetailInput
        label={words.street}
        value={draft.street}
        maxLength={55}
        error={errors.street}
        onChange={(street) => onChange({ street })}
        className="sm:col-span-2"
      />
      <DetailInput
        label={words.street2}
        value={draft.street_2}
        maxLength={55}
        optional
        onChange={(street_2) => onChange({ street_2 })}
        className="sm:col-span-2"
      />
      <DetailInput label={words.city} value={draft.city} maxLength={30} error={errors.city} onChange={(city) => onChange({ city })} />
      <div className="grid grid-cols-2 gap-4">
        <DetailInput label={words.state} value={draft.state} maxLength={2} error={errors.state} onChange={(state) => onChange({ state })} />
        <DetailInput label={words.zip} value={draft.zip_code} maxLength={10} error={errors.zip_code} onChange={(zip_code) => onChange({ zip_code })} />
      </div>
    </>
  );
}
