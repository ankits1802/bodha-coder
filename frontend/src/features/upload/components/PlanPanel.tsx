import { DatePicker } from "@/components/ui/DatePicker";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { VISIT_TYPES } from "@/lib/labels";
import { UPLOAD_TEXT } from "../strings";
import { includedEntries, sharedValue, type Placement, type References, type UploadEntry } from "../uploadEntries";
import { MIXED_PAYER, batchPayerOptions, sharedPayer } from "../uploadPayers";
import { placeOptions, providerOptions } from "./placementOptions";

interface PlanPanelProps {
  entries: UploadEntry[];
  references: References;
  visitType: string;
  onPlace: (change: Partial<Placement>) => void;
  onPayer: (payerId: string) => void;
  onVisitType: (visitType: string) => void;
}

export function PlanPanel({ entries, references, visitType, onPlace, onPayer, onVisitType }: PlanPanelProps) {
  const words = UPLOAD_TEXT.plan;
  const providerId = sharedValue(entries, "providerId");
  const serviceDate = sharedValue(entries, "serviceDate");
  const placeCode = sharedValue(entries, "placeCode");
  const payer = sharedPayer(includedEntries(entries));
  const blank = (value: string, choose: string) => (value || entries.length < 2 ? choose : words.mixed);

  return (
    <section
      aria-label={words.label}
      className="grid grid-cols-[repeat(auto-fit,minmax(12.5rem,1fr))] gap-4.5 rounded-panel bg-surface p-5 shadow-panel"
    >
      <Field label={words.provider}>
        {(control) => (
          <Select
            {...control}
            value={providerId}
            options={providerOptions(references.providers, blank(providerId, words.chooseProvider))}
            onChange={(chosen) => onPlace({ providerId: chosen })}
          />
        )}
      </Field>
      <Field label={words.date}>
        {(control) => (
          <DatePicker
            {...control}
            value={serviceDate || null}
            onChange={(day) => {
              if (day) onPlace({ serviceDate: day });
            }}
          />
        )}
      </Field>
      <Field label={words.place}>
        {(control) => (
          <Select
            {...control}
            value={placeCode}
            options={placeOptions(references.places, blank(placeCode, words.choosePlace))}
            onChange={(chosen) => onPlace({ placeCode: chosen })}
          />
        )}
      </Field>
      {references.payers.length > 0 ? (
        <Field label={words.payer} optional={words.recommended}>
          {(control) => (
            <Select
              {...control}
              value={payer ?? MIXED_PAYER}
              options={batchPayerOptions(references.payers, payer)}
              onChange={(chosen) => {
                if (chosen !== MIXED_PAYER) onPayer(chosen);
              }}
            />
          )}
        </Field>
      ) : null}
      <Field label={words.visitType}>
        {(control) => (
          <Select {...control} value={visitType} options={VISIT_TYPES.map((type) => ({ value: type, label: type }))} onChange={onVisitType} />
        )}
      </Field>
    </section>
  );
}
