import { Field } from "@/components/ui/Field";
import { Input, Select } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { QualityOptions } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { SCOPES, defaultSize, toggled, type SampleDraft } from "../sampleDraft";
import { QUALITY_TEXT } from "../strings";

interface SampleFieldsProps {
  draft: SampleDraft;
  options: QualityOptions;
  onChange: (draft: SampleDraft) => void;
}

const SCOPE_SEGMENTS = SCOPES.map((value) => ({ value, label: QUALITY_TEXT.scopeLabels[value] }));

export function SampleFields({ draft, options, onChange }: SampleFieldsProps) {
  const words = QUALITY_TEXT.dialog;
  const set = (changes: Partial<SampleDraft>) => onChange({ ...draft, ...changes });
  return (
    <>
      <SegmentedControl label={words.scope} value={draft.scope} segments={SCOPE_SEGMENTS} onChange={(scope) => set({ scope })} />
      {draft.scope === "provider" ? (
        <Field label={words.provider}>
          {(control) => (
            <Select {...control} value={draft.providerId} onChange={(event) => set({ providerId: event.target.value })}>
              <option value="">{words.choose}</option>
              {options.providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      ) : null}
      {draft.scope === "specialty" ? (
        <Field label={words.specialty}>
          {(control) => (
            <Select {...control} value={draft.specialty} onChange={(event) => set({ specialty: event.target.value })}>
              <option value="">{words.choose}</option>
              {options.specialties.map((specialty) => (
                <option key={specialty}>{specialty}</option>
              ))}
            </Select>
          )}
        </Field>
      ) : null}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Field label={words.start}>
          {(control) => <Input {...control} type="date" value={draft.start} onChange={(event) => set({ start: event.target.value })} />}
        </Field>
        <Field label={words.end}>
          {(control) => <Input {...control} type="date" value={draft.end} onChange={(event) => set({ end: event.target.value })} />}
        </Field>
        <Field label={words.size}>
          {(control) => (
            <Input
              {...control}
              inputMode="numeric"
              placeholder={String(defaultSize(draft, options))}
              value={draft.size}
              onChange={(event) => set({ size: event.target.value.trim() })}
            />
          )}
        </Field>
      </div>
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="mb-1.5 p-0 text-subhead font-medium text-label">{words.reviewers}</legend>
        {options.reviewers.map((reviewer) => (
          <label key={reviewer.id} className="flex items-center gap-2.5 text-body">
            <input
              type="checkbox"
              className="size-4 accent-label"
              checked={draft.reviewerIds.includes(reviewer.id)}
              onChange={() => set({ reviewerIds: toggled(draft.reviewerIds, reviewer.id) })}
            />
            {reviewer.name}
            <span className="text-footnote text-secondary">{ROLE_LABELS[reviewer.role]}</span>
          </label>
        ))}
      </fieldset>
    </>
  );
}
