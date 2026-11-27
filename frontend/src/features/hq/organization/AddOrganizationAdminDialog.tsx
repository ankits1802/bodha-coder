"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { addOrganizationAdmin } from "@/lib/api/hqOrganizations";
import { isEmail } from "@/lib/validation";
import { TextField } from "../practices/FormFields";
import { HQ_TEXT } from "../strings";

const FORM_ID = "add-organization-admin";
const REASON_MIN = 3;
const REASON_MAX = 200;
const words = HQ_TEXT.organization.admins;

interface AddOrganizationAdminDialogProps {
  organization: { id: string; name: string };
  onClose: () => void;
  onAdded: (email: string) => void;
}

export function AddOrganizationAdminDialog({ organization, onClose, onAdded }: AddOrganizationAdminDialogProps) {
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);
  const add = useAction(addOrganizationAdmin);
  const emailError = touched && !isEmail(email) ? words.emailError : null;
  const reasonError = touched && reason.trim().length < REASON_MIN ? words.reasonError : null;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTouched(true);
    if (!isEmail(email) || reason.trim().length < REASON_MIN) return;
    const outcome = await add.run(organization.id, { email: email.trim(), reason: reason.trim() });
    if (outcome.ok) onAdded(email.trim());
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.addTitle(organization.name)}
      footer={
        <>
          <Button onClick={onClose}>{HQ_TEXT.organization.confirm.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={add.pending}>
            {words.submit}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
        <TextField label={words.email} type="email" autoComplete="off" value={email} error={emailError} onChange={setEmail} />
        <TextField label={words.reason} maxLength={REASON_MAX} value={reason} error={reasonError} onChange={setReason} />
        {add.error ? <InlineAlert tone="bad">{add.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
