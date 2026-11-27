"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { TextArea } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { grantOwnAccess } from "@/lib/api/organizations";
import type { MyOrganizationPractice, PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { ORGANIZATION_TEXT } from "./strings";

interface GetAccessDialogProps {
  organizationId: string;
  practice: MyOrganizationPractice;
  onClose: () => void;
  onGranted: () => void;
  onOpen: (practiceId: string) => void;
}

const words = ORGANIZATION_TEXT.access;
const ROLE_OPTIONS = PRACTICE_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }));
const REASON_MIN = 3;
const REASON_MAX = 200;

export function GetAccessDialog({ organizationId, practice, onClose, onGranted, onOpen }: GetAccessDialogProps) {
  const [role, setRole] = useState<PracticeRole>("viewer");
  const [reason, setReason] = useState("");
  const [granted, setGranted] = useState(false);
  const grant = useAction(grantOwnAccess);
  const trimmed = reason.trim();
  const reasonError = trimmed.length > 0 && trimmed.length < REASON_MIN ? words.reasonLength : null;

  async function submit(): Promise<void> {
    if (!(await grant.run(organizationId, practice.id, { role, reason: trimmed })).ok) return;
    setGranted(true);
    onGranted();
  }

  const footer = granted ? (
    <>
      <Button variant="plain" onClick={onClose}>
        {words.close}
      </Button>
      <Button variant="primary" onClick={() => onOpen(practice.id)}>
        {ORGANIZATION_TEXT.practices.openFor(practice.name)}
      </Button>
    </>
  ) : (
    <>
      <Button variant="plain" onClick={onClose}>
        {words.cancel}
      </Button>
      <Button variant="primary" pending={grant.pending} disabled={trimmed.length < REASON_MIN} onClick={() => void submit()}>
        {words.give}
      </Button>
    </>
  );

  return (
    <Dialog open onClose={onClose} title={words.title(practice.name)} footer={footer}>
      {granted ? (
        <InlineAlert tone="ok">{words.granted(practice.name)}</InlineAlert>
      ) : (
        <div className="flex flex-col gap-4">
          <Field label={words.role}>
            {(control) => <Select {...control} value={role} options={ROLE_OPTIONS} onChange={setRole} />}
          </Field>
          <Field label={words.reason} error={reasonError}>
            {(control) => (
              <TextArea {...control} maxLength={REASON_MAX} value={reason} onChange={(event) => setReason(event.target.value)} />
            )}
          </Field>
        </div>
      )}
      {grant.error ? <InlineAlert tone="bad">{grant.error}</InlineAlert> : null}
    </Dialog>
  );
}
