"use client";

import { useState } from "react";
import { InviteDialog as SharedInviteDialog, type InvitedPerson } from "@/components/shared/InviteDialog";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { inviteMember } from "@/lib/api/team";
import type { PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { TEAM_TEXT } from "./strings";

interface InviteDialogProps {
  onClose: () => void;
  onInvited: () => void;
}

export function InviteDialog({ onClose, onInvited }: InviteDialogProps) {
  const [role, setRole] = useState<PracticeRole>("coder");
  const words = TEAM_TEXT.inviteDialog;

  return (
    <SharedInviteDialog
      title={words.title}
      formId="invite-member"
      invite={(person: InvitedPerson) => inviteMember({ ...person, role })}
      onClose={onClose}
      onInvited={onInvited}
    >
      <Field label={words.role}>
        {(control) => (
          <Select
            {...control}
            value={role}
            options={PRACTICE_ROLES.map((option) => ({ value: option, label: ROLE_LABELS[option] }))}
            onChange={setRole}
          />
        )}
      </Field>
    </SharedInviteDialog>
  );
}
