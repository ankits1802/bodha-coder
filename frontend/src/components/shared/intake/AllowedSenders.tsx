"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { allowIntakeSender, removeIntakeSender } from "@/lib/api/emailIntake";
import type { EmailIntake, IntakeSender } from "@/lib/api/types";
import { EMAIL_INTAKE_TEXT } from "./strings";

interface AllowedSendersProps {
  senders: readonly IntakeSender[];
  onChange: (intake: EmailIntake) => void;
}

const words = EMAIL_INTAKE_TEXT;

export function AllowedSenders({ senders, onChange }: AllowedSendersProps) {
  const [sender, setSender] = useState("");
  const allow = useAction(allowIntakeSender);
  const remove = useAction(removeIntakeSender);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const outcome = await allow.run(sender.trim());
    if (!outcome.ok) return;
    setSender("");
    onChange(outcome.value);
  }

  async function drop(senderId: string): Promise<void> {
    const outcome = await remove.run(senderId);
    if (outcome.ok) onChange(outcome.value);
  }

  return (
    <div className="flex flex-col gap-3 border-t border-hairline px-4 py-4">
      <span className="text-subhead font-medium text-label">{words.senders}</span>
      {senders.length > 0 ? (
        <ul aria-label={words.senders} className="m-0 flex list-none flex-col gap-1 p-0">
          {senders.map((item) => (
            <li key={item.id} className="flex min-h-9 items-center justify-between gap-3 text-body">
              <span className="min-w-0 break-all text-label">{item.pattern}</span>
              <Button size="sm" variant="plain" aria-label={words.removeFor(item.pattern)} disabled={remove.pending} onClick={() => void drop(item.id)}>
                {words.remove}
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <span className="text-subhead text-secondary">{words.noSenders}</span>
      )}
      {remove.error ? <InlineAlert tone="bad">{remove.error}</InlineAlert> : null}
      <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-wrap items-end gap-3">
        <Field label={words.sender} error={allow.error} className="min-w-56 flex-1">
          {(control) => (
            <Input
              {...control}
              value={sender}
              autoComplete="off"
              spellCheck={false}
              onChange={(event) => {
                setSender(event.target.value);
                allow.clearError();
              }}
            />
          )}
        </Field>
        <Button type="submit" pending={allow.pending} disabled={sender.trim().length === 0}>
          {words.allow}
        </Button>
      </form>
    </div>
  );
}
