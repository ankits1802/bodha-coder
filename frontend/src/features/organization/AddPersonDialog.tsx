"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { addOrganizationPerson } from "@/lib/api/organizations";
import type { OrganizationPracticeRow } from "@/lib/api/types";
import { isEmail } from "@/lib/validation";
import { PlacementRows, chosenPlacements, type PlacementChoice } from "./PlacementRows";
import { ORGANIZATION_TEXT } from "./strings";

interface AddPersonDialogProps {
  organizationId: string;
  practices: readonly Pick<OrganizationPracticeRow, "id" | "name">[];
  onClose: () => void;
  onAdded: (name: string) => void;
}

const words = ORGANIZATION_TEXT.person;

export function AddPersonDialog({ organizationId, practices, onClose, onAdded }: AddPersonDialogProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [choices, setChoices] = useState<Record<string, PlacementChoice>>({});
  const [checked, setChecked] = useState(false);
  const add = useAction(addOrganizationPerson);
  const placements = chosenPlacements(choices);
  const errors = {
    name: checked && !name.trim() ? words.nameNeeded : null,
    email: checked && !isEmail(email.trim()) ? words.emailNeeded : null,
    practices: checked && placements.length === 0 ? words.choosePractice : null,
  };

  async function submit(): Promise<void> {
    setChecked(true);
    if (!name.trim() || !isEmail(email.trim()) || placements.length === 0) return;
    const body = { name: name.trim(), email: email.trim(), practices: placements };
    if ((await add.run(organizationId, body)).ok) onAdded(body.name);
  }

  const footer = (
    <>
      <Button variant="plain" onClick={onClose}>
        {words.cancel}
      </Button>
      <Button variant="primary" pending={add.pending} onClick={() => void submit()}>
        {words.add}
      </Button>
    </>
  );

  return (
    <Dialog open onClose={onClose} title={words.title} footer={footer}>
      <div className="flex flex-col gap-4">
        <Field label={words.name} error={errors.name}>
          {(control) => <Input {...control} autoComplete="off" value={name} onChange={(event) => setName(event.target.value)} />}
        </Field>
        <Field label={words.email} error={errors.email}>
          {(control) => (
            <Input {...control} type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} />
          )}
        </Field>
        <PlacementRows
          practices={practices}
          choices={choices}
          error={errors.practices}
          onChange={(practiceId, choice) => setChoices((current) => ({ ...current, [practiceId]: choice }))}
        />
        {add.error ? <InlineAlert tone="bad">{add.error}</InlineAlert> : null}
      </div>
    </Dialog>
  );
}
