import { DateRange } from "@/components/ui/DateRange";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { Select } from "@/components/ui/Select";
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
            <Select
              {...control}
              value={draft.providerId}
              options={[{ value: "", label: words.choose }, ...options.providers.map((provider) => ({ value: provider.id, label: provider.name }))]}
              onChange={(providerId) => set({ providerId })}
            />
          )}
        </Field>
      ) : null}
      {draft.scope === "specialty" ? (
        <Field label={words.specialty}>
          {(control) => (
            <Select
              {...control}
              value={draft.specialty}
              options={[{ value: "", label: words.choose }, ...options.specialties.map((specialty) => ({ value: specialty, label: specialty }))]}
              onChange={(specialty) => set({ specialty })}
            />
          )}
        </Field>
      ) : null}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <DateRange
          start={draft.start || null}
          end={draft.end || null}
          labels={{ start: words.start, end: words.end }}
          onChange={(range) => set({ start: range.start ?? "", end: range.end ?? "" })}
        />
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
