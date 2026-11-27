"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { TextArea } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { requestDemo } from "@/lib/api/hq";
import { useSession } from "@/lib/session/useSession";
import { PLAN_TEXT } from "./strings";

const words = PLAN_TEXT.sales;
const MESSAGE_LIMIT = 2000;

export function ContactSales() {
  const { user } = useSession();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const send = useAction(requestDemo);

  async function submit(): Promise<void> {
    if (!user) return;
    const organization = user.practice?.name ?? user.name;
    const body = { name: user.name, email: user.email, organization, message: message.trim() || null };
    if ((await send.run(body)).ok) setSent(true);
  }

  const footer = sent ? (
    <Button onClick={() => setOpen(false)}>{words.close}</Button>
  ) : (
    <>
      <Button variant="plain" onClick={() => setOpen(false)}>
        {words.cancel}
      </Button>
      <Button variant="primary" pending={send.pending} onClick={() => void submit()}>
        {words.send}
      </Button>
    </>
  );

  return (
    <>
      <Button aria-haspopup="dialog" onClick={() => setOpen(true)}>
        {words.button}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title={words.title} footer={footer}>
        {sent ? (
          <InlineAlert tone="ok">{words.sent}</InlineAlert>
        ) : (
          <Field label={words.message} optional={words.optional}>
            {(control) => (
              <TextArea
                {...control}
                maxLength={MESSAGE_LIMIT}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
              />
            )}
          </Field>
        )}
        {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
      </Dialog>
    </>
  );
}
