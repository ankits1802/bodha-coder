"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAssignees } from "@/hooks/useAssignees";
import type { User } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { QUEUE_TEXT } from "../strings";

const NOBODY = "nobody";

interface AssignDialogProps {
  open: boolean;
  count: number;
  member: User;
  pending: boolean;
  error: string | null;
  onClose: () => void;
  onAssign: (userId: string | null) => void;
}

function PersonField({ member, value, onChange }: { member: User; value: string; onChange: (value: string) => void }) {
  const assignees = useAssignees(member);
  return (
    <>
      <Field label={QUEUE_TEXT.assignee}>
        {(control) => (
          <Select
            {...control}
            value={value}
            options={[
              { value: "", label: QUEUE_TEXT.choosePerson, disabled: true },
              ...assignees.people.map((person) => ({ value: person.id, label: person.name })),
              { value: NOBODY, label: QUEUE_TEXT.nobody },
            ]}
            onChange={onChange}
          />
        )}
      </Field>
      {assignees.error ? <InlineAlert tone="bad">{assignees.error}</InlineAlert> : null}
    </>
  );
}

export function AssignDialog({ open, count, member, pending, error, onClose, onAssign }: AssignDialogProps) {
  const [choice, setChoice] = useState("");
  const close = () => {
    setChoice("");
    onClose();
  };
  const footer = (
    <>
      <Button onClick={close}>{QUEUE_TEXT.cancel}</Button>
      <Button variant="primary" disabled={!choice} pending={pending} onClick={() => onAssign(choice === NOBODY ? null : choice)}>
        {QUEUE_TEXT.assignConfirm}
      </Button>
    </>
  );
  return (
    <Dialog open={open} onClose={close} title={QUEUE_TEXT.assignTitle(count, formatCount(count))} footer={footer}>
      <PersonField member={member} value={choice} onChange={setChoice} />
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
    </Dialog>
  );
}
