"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input, TextArea } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { requestDemo } from "@/lib/api/hq";
import { demoProblems, EMPTY_DEMO, toDemoRequest, type DemoDraft, type DemoProblems } from "./demoForm";
import { LANDING_TEXT } from "./strings";

const words = LANDING_TEXT.form;

export function DemoRequestForm({ onClose }: { onClose: () => void }) {
  const [draft, setDraft] = useState<DemoDraft>(EMPTY_DEMO);
  const [problems, setProblems] = useState<DemoProblems>({});
  const [sent, setSent] = useState(false);
  const send = useAction(requestDemo);

  const edit = (field: keyof DemoDraft) => (value: string) => setDraft((current) => ({ ...current, [field]: value }));

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = demoProblems(draft);
    setProblems(found);
    if (Object.keys(found).length > 0) return;
    const outcome = await send.run(toDemoRequest(draft));
    if (outcome.ok) setSent(true);
  }

  if (sent) {
    return (
      <div className="flex flex-col gap-4">
        <InlineAlert tone="ok">{words.sent}</InlineAlert>
        <Button onClick={onClose} className="self-end">
          {words.close}
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-4">
      <Field label={words.name} error={problems.name}>
        {(control) => <Input {...control} autoComplete="name" value={draft.name} onChange={(e) => edit("name")(e.target.value)} />}
      </Field>
      <Field label={words.email} error={problems.email}>
        {(control) => (
          <Input {...control} type="email" autoComplete="email" value={draft.email} onChange={(e) => edit("email")(e.target.value)} />
        )}
      </Field>
      <Field label={words.organization} error={problems.organization}>
        {(control) => (
          <Input {...control} autoComplete="organization" value={draft.organization} onChange={(e) => edit("organization")(e.target.value)} />
        )}
      </Field>
      <Field label={words.message} optional={words.optional}>
        {(control) => <TextArea {...control} value={draft.message} onChange={(e) => edit("message")(e.target.value)} />}
      </Field>
      {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <Button onClick={onClose}>{words.cancel}</Button>
        <Button type="submit" variant="primary" pending={send.pending}>
          {words.submit}
        </Button>
      </div>
    </form>
  );
}
