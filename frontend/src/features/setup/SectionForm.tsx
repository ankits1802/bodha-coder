"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { saveSetupSection } from "@/lib/api/practice";
import type { SetupSection, SetupSectionKey } from "@/lib/api/types";
import { fieldError, fieldLabel, sameValues, valuesFor } from "./setupModel";
import { SETUP_TEXT } from "./strings";

interface SectionFormProps {
  sectionKey: SetupSectionKey;
  section: SetupSection;
  onSaved: () => void;
}

export function SectionForm({ sectionKey, section, onSaved }: SectionFormProps) {
  const stored = valuesFor(section.fields, section.values);
  const [values, setValues] = useState(stored);
  const [touched, setTouched] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const save = useAction(saveSetupSection);
  const dirty = !sameValues(values, stored);
  const formId = `setup-${sectionKey}`;
  const errorOf = (field: string) => (touched.includes(field) ? fieldError(field, values[field] ?? "") : null);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTouched(section.fields);
    if (section.fields.some((field) => fieldError(field, values[field] ?? ""))) return;
    const outcome = await save.run(sectionKey, values);
    if (!outcome.ok) return;
    setSaved(true);
    onSaved();
  }

  function change(field: string, value: string): void {
    setSaved(false);
    setValues((current) => ({ ...current, [field]: value }));
  }

  return (
    <Panel aria-labelledby={`${formId}-title`}>
      <PanelHeader title={<span id={`${formId}-title`}>{SETUP_TEXT.sections[sectionKey]}</span>} />
      <form id={formId} onSubmit={submit} noValidate className="grid gap-4 px-4 pb-4 sm:grid-cols-2">
        {section.fields.map((field) => (
          <Field key={field} label={fieldLabel(field)} error={errorOf(field)}>
            {(control) => (
              <Input
                {...control}
                value={values[field] ?? ""}
                onChange={(event) => change(field, event.target.value)}
                onBlur={() => setTouched((current) => (current.includes(field) ? current : [...current, field]))}
              />
            )}
          </Field>
        ))}
        <div className="flex flex-wrap items-center justify-end gap-3 sm:col-span-2">
          {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
          {saved && !dirty ? (
            <span role="status" className="text-subhead text-secondary">
              {SETUP_TEXT.saved}
            </span>
          ) : null}
          <Button type="submit" variant="primary" pending={save.pending} disabled={!dirty}>
            {SETUP_TEXT.save}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
