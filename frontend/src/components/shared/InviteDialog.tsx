"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { isEmail } from "@/lib/validation";
import { SHARED_TEXT } from "./strings";

export interface InvitedPerson {
  name: string;
  email: string;
}

interface InviteDialogProps {
  title: string;
  formId: string;
  invite: (person: InvitedPerson) => Promise<unknown>;
  onClose: () => void;
  onInvited: () => void;
  children?: ReactNode;
  submitLabel?: string;
  ready?: () => boolean;
}

export function InviteDialog(props: InviteDialogProps) {
  const { title, formId, invite, onClose, onInvited, children, submitLabel, ready = () => true } = props;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState<string[]>([]);
  const sending = useAction(invite);
  const words = SHARED_TEXT.invite;
  const touch = (field: string) => setTouched((current) => (current.includes(field) ? current : [...current, field]));
  const nameError = touched.includes("name") && !name.trim() ? words.errors.name : null;
  const emailError = touched.includes("email") && !isEmail(email) ? words.errors.email : null;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTouched(["name", "email"]);
    const extrasReady = ready();
    if (!name.trim() || !isEmail(email) || !extrasReady) return;
    const outcome = await sending.run({ name: name.trim(), email: email.trim() });
    if (outcome.ok) onInvited();
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={formId} variant="primary" pending={sending.pending}>
            {submitLabel ?? words.send}
          </Button>
        </>
      }
    >
      <form id={formId} noValidate onSubmit={submit} className="flex flex-col gap-4">
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
        {children}
        {sending.error ? <InlineAlert tone="bad">{sending.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
