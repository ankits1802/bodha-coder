"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { InviteRowFields, ROW_GRID } from "./InviteRowFields";
import { FIRST_ROWS, blankRow, blankRows, filledRows, nextRowId, readyToSend, rowErrors, type InviteRow } from "./inviteRows";
import { sendInvites } from "./sendInvites";
import { INVITE_ROWS_TEXT } from "./strings";

const FORM_ID = "invite-rows";

interface InviteRowsDialogProps {
  onClose: () => void;
  onSent: (count: number) => void;
}

export function InviteRowsDialog({ onClose, onSent }: InviteRowsDialogProps) {
  const [rows, setRows] = useState<InviteRow[]>(() => blankRows(FIRST_ROWS));
  const [tried, setTried] = useState(false);
  const [sending, setSending] = useState(false);
  const filled = filledRows(rows);
  const words = INVITE_ROWS_TEXT;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTried(true);
    if (!readyToSend(rows)) return;
    setSending(true);
    const outcome = await sendInvites(filled);
    setSending(false);
    if (outcome.sent > 0) onSent(outcome.sent);
    if (outcome.failed.length === 0) onClose();
    else setRows(outcome.failed);
  }

  const footer = (
    <>
      <Button onClick={onClose} disabled={sending}>
        {words.cancel}
      </Button>
      <Button type="submit" form={FORM_ID} variant="primary" pending={sending}>
        {filled.length > 0 ? words.send(filled.length) : words.sendNone}
      </Button>
    </>
  );
  return (
    <Dialog open onClose={onClose} size="lg" title={words.title} footer={footer}>
      <form id={FORM_ID} noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-3">
        <div aria-hidden="true" className={`${ROW_GRID} hidden text-subhead font-medium sm:grid`}>
          <span>{words.name}</span>
          <span>{words.email}</span>
          <span>{words.role}</span>
        </div>
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {rows.map((row, index) => (
            <InviteRowFields
              key={row.id}
              row={row}
              number={index + 1}
              errors={tried ? rowErrors(row) : {}}
              removable={rows.length > 1}
              onChange={(next) => setRows((current) => current.map((item) => (item.id === next.id ? next : item)))}
              onRemove={() => setRows((current) => current.filter((item) => item.id !== row.id))}
            />
          ))}
        </ul>
        <Button size="sm" className="self-start" onClick={() => setRows((current) => [...current, blankRow(nextRowId(current))])}>
          {words.addRow}
        </Button>
        {tried && filled.length === 0 ? <InlineAlert tone="bad">{words.errors.nobody}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
