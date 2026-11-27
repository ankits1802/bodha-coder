"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { addOrganization, updateOrganization } from "@/lib/api/hqOrganizations";
import type { HqOrganization, Plan } from "@/lib/api/types";
import { PLAN_LABELS } from "@/lib/labels";
import { ChoiceField, TextField } from "../practices/FormFields";
import { PLANS } from "../practices/practiceForm";
import { HQ_TEXT } from "../strings";

const FORM_ID = "organization-form";
const NAME_MIN = 2;
const words = HQ_TEXT.organizations.form;

interface OrganizationDialogProps {
  organization?: Pick<HqOrganization, "id" | "name" | "plan">;
  onClose: () => void;
  onSaved: (name: string) => void;
}

async function save(organization: OrganizationDialogProps["organization"], name: string, plan: Plan): Promise<void> {
  if (!organization) {
    await addOrganization({ name, plan });
    return;
  }
  const update = {
    ...(name !== organization.name ? { name } : {}),
    ...(plan !== organization.plan ? { plan } : {}),
  };
  await updateOrganization(organization.id, update);
}

export function OrganizationDialog({ organization, onClose, onSaved }: OrganizationDialogProps) {
  const [name, setName] = useState(organization?.name ?? "");
  const [plan, setPlan] = useState<Plan>(organization?.plan ?? "trial");
  const [touched, setTouched] = useState(false);
  const run = useAction(save);
  const tooShort = name.trim().length < NAME_MIN;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTouched(true);
    if (tooShort) return;
    const outcome = await run.run(organization, name.trim(), plan);
    if (outcome.ok) onSaved(name.trim());
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={organization ? words.editTitle(organization.name) : words.addTitle}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={run.pending}>
            {organization ? words.save : words.add}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
        <TextField label={words.name} value={name} maxLength={200} error={touched && tooShort ? words.nameError : null} onChange={setName} />
        <ChoiceField label={words.plan} value={plan} options={PLANS} labels={PLAN_LABELS} onChange={setPlan} />
        {run.error ? <InlineAlert tone="bad">{run.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
