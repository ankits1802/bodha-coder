"use client";

import { useState } from "react";
import { InviteDialog, type InvitedPerson } from "@/components/shared/InviteDialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { appointAdmin } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";

const REASON_MIN = 3;
const REASON_MAX = 200;

interface AppointAdminDialogProps {
  practice: HqPractice;
  onClose: () => void;
  onAppointed: () => void;
}

export function AppointAdminDialog({ practice, onClose, onAppointed }: AppointAdminDialogProps) {
  const words = HQ_TEXT.practices.appoint;
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);
  const tooShort = reason.trim().length < REASON_MIN;

  function ready(): boolean {
    setTouched(true);
    return !tooShort;
  }

  return (
    <InviteDialog
      title={words.title(practice.name)}
      formId="appoint-admin"
      submitLabel={words.submit}
      ready={ready}
      invite={(person: InvitedPerson) => appointAdmin(practice.id, { ...person, reason: reason.trim() })}
      onClose={onClose}
      onInvited={onAppointed}
    >
      <Field label={words.reason} error={touched && tooShort ? words.reasonError : null}>
        {(control) => (
          <Input
            {...control}
            maxLength={REASON_MAX}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            onBlur={() => setTouched(true)}
          />
        )}
      </Field>
    </InviteDialog>
  );
}
