"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input, Select } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { inviteMember } from "@/lib/api/team";
import type { PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { isEmail } from "@/lib/validation";
import { TEAM_TEXT } from "./strings";

const FORM_ID = "invite-member";

interface InviteDialogProps {
  onClose: () => void;
  onInvited: () => void;
}

export function InviteDialog({ onClose, onInvited }: InviteDialogProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<PracticeRole>("coder");
  const [touched, setTouched] = useState<string[]>([]);
  const invite = useAction(inviteMember);
  const words = TEAM_TEXT.inviteDialog;
  const touch = (field: string) => setTouched((current) => (current.includes(field) ? current : [...current, field]));
  const nameError = touched.includes("name") && !name.trim() ? words.errors.name : null;
  const emailError = touched.includes("email") && !isEmail(email) ? words.errors.email : null;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTouched(["name", "email"]);
    if (!name.trim() || !isEmail(email)) return;
    const outcome = await invite.run({ name: name.trim(), email: email.trim(), role });
    if (outcome.ok) onInvited();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.title}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={invite.pending}>
            {words.send}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={submit} className="flex flex-col gap-4">
        <Field label={words.name} error={nameError}>
          {(control) => (
            <Input {...control} autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} onBlur={() => touch("name")} />
          )}
        </Field>
        <Field label={words.email} error={emailError}>
          {(control) => (
            <Input
              {...control}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              onBlur={() => touch("email")}
            />
          )}
        </Field>
        <Field label={words.role}>
          {(control) => (
            <Select {...control} value={role} onChange={(event) => setRole(event.target.value as PracticeRole)}>
              {PRACTICE_ROLES.map((option) => (
                <option key={option} value={option}>
                  {ROLE_LABELS[option]}
                </option>
              ))}
            </Select>
          )}
        </Field>
        {invite.error ? <InlineAlert tone="bad">{invite.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
