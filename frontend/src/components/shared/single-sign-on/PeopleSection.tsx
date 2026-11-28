import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { SsoNewPersonRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { NEW_PERSON_ROLES, type SsoDraft } from "./ssoDraft";
import { SSO_TEXT } from "./strings";
import { ToggleRow } from "./ToggleRow";

interface PeopleSectionProps {
  draft: SsoDraft;
  onChange: (next: Partial<SsoDraft>) => void;
}

const ROLE_OPTIONS = NEW_PERSON_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }));

function TextField({ label, value, placeholder, onChange }: { label: string; value: string; placeholder?: string; onChange: (value: string) => void }) {
  return (
    <Field label={label} optional={SSO_TEXT.optional} className="min-w-56 flex-1">
      {(control) => (
        <Input
          {...control}
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </Field>
  );
}

export function PeopleSection({ draft, onChange }: PeopleSectionProps) {
  return (
    <section aria-label={SSO_TEXT.people} className="flex flex-col gap-4 border-t border-hairline px-4 py-4">
      <h3 className="m-0 text-body font-semibold">{SSO_TEXT.people}</h3>
      <div className="flex flex-wrap gap-3">
        <TextField
          label={SSO_TEXT.emailAttribute}
          value={draft.emailAttribute}
          placeholder={SSO_TEXT.emailFromNameId}
          onChange={(emailAttribute) => onChange({ emailAttribute })}
        />
        <TextField label={SSO_TEXT.nameAttribute} value={draft.nameAttribute} onChange={(nameAttribute) => onChange({ nameAttribute })} />
      </div>
      <TextField
        label={SSO_TEXT.mfaContext}
        value={draft.mfaContext}
        placeholder={SSO_TEXT.mfaPlaceholder}
        onChange={(mfaContext) => onChange({ mfaContext })}
      />
      <ToggleRow label={SSO_TEXT.createPeople} checked={draft.createPeople} onChange={(createPeople) => onChange({ createPeople })} />
      {draft.createPeople ? (
        <Field label={SSO_TEXT.newPersonRole} className="max-w-80">
          {(control) => (
            <Select<SsoNewPersonRole>
              {...control}
              value={draft.newPersonRole}
              options={ROLE_OPTIONS}
              onChange={(newPersonRole) => onChange({ newPersonRole })}
            />
          )}
        </Field>
      ) : null}
    </section>
  );
}
