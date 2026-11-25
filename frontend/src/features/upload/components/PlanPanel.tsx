import { Field } from "@/components/ui/Field";
import { Input, Select } from "@/components/ui/Input";
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
          <Select {...control} value={plan.provider_id} onChange={(event) => chooseProvider(event.target.value)}>
            <option value="">{words.chooseProvider}</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {words.providerOption(provider.name, provider.credential)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={words.date}>
        {(control) => (
          <Input
            {...control}
            type="date"
            value={plan.service_date}
            onChange={(event) => onChange({ ...plan, service_date: event.target.value })}
          />
        )}
      </Field>
      <Field label={words.place}>
        {(control) => (
          <Select {...control} value={plan.place_code} onChange={(event) => onChange({ ...plan, place_code: event.target.value })}>
            <option value="">{words.choosePlace}</option>
            {places.map((place) => (
              <option key={place.code} value={place.code}>
                {words.placeOption(place.name, place.code)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={words.visitType}>
        {(control) => (
          <Select {...control} value={plan.visit_type} onChange={(event) => onChange({ ...plan, visit_type: event.target.value })}>
            {VISIT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </Select>
        )}
      </Field>
    </section>
  );
}
