import { DatePicker } from "@/components/ui/DatePicker";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import type { Place, Provider, UploadPlan } from "@/lib/api/types";
import { VISIT_TYPES } from "@/lib/labels";
import { UPLOAD_TEXT } from "../strings";

interface PlanPanelProps {
  plan: UploadPlan;
  providers: Provider[];
  places: Place[];
  onChange: (plan: UploadPlan) => void;
}

export function PlanPanel({ plan, providers, places, onChange }: PlanPanelProps) {
  const words = UPLOAD_TEXT.plan;

  function chooseProvider(providerId: string): void {
    const provider = providers.find((item) => item.id === providerId);
    const usual = provider?.place_code && places.some((place) => place.code === provider.place_code) ? provider.place_code : null;
    onChange({ ...plan, provider_id: providerId, place_code: usual ?? plan.place_code });
  }

  return (
    <section
      aria-label={words.label}
      className="grid grid-cols-[repeat(auto-fit,minmax(12.5rem,1fr))] gap-4.5 rounded-panel bg-surface p-5 shadow-panel"
    >
      <Field label={words.provider}>
        {(control) => (
          <Select
            {...control}
            value={plan.provider_id}
            options={[
              { value: "", label: words.chooseProvider },
              ...providers.map((provider) => ({ value: provider.id, label: words.providerOption(provider.name, provider.credential) })),
            ]}
            onChange={chooseProvider}
          />
        )}
      </Field>
      <Field label={words.date}>
        {(control) => (
          <DatePicker {...control} value={plan.service_date || null} onChange={(day) => onChange({ ...plan, service_date: day ?? "" })} />
        )}
      </Field>
      <Field label={words.place}>
        {(control) => (
          <Select
            {...control}
            value={plan.place_code}
            options={[{ value: "", label: words.choosePlace }, ...places.map((place) => ({ value: place.code, label: words.placeOption(place.name, place.code) }))]}
            onChange={(place_code) => onChange({ ...plan, place_code })}
          />
        )}
      </Field>
      <Field label={words.visitType}>
        {(control) => (
          <Select
            {...control}
            value={plan.visit_type}
            options={VISIT_TYPES.map((type) => ({ value: type, label: type }))}
            onChange={(visit_type) => onChange({ ...plan, visit_type })}
          />
        )}
      </Field>
    </section>
  );
}
