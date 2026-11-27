"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { DefensePacketButton } from "@/components/shared/defense/DefensePacketButton";
import { ReasonDialog } from "@/components/shared/ReasonDialog";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { voidNotes } from "@/lib/api/notes";
import type { NoteHeader } from "@/lib/api/types";
import { VISIT_TYPES } from "@/lib/labels";
import { VOID_REASON_MAX, VOID_REASON_MIN } from "@/lib/validation";
import type { ReviewPermissions } from "../permissions";
import { REVIEW_TEXT } from "../strings";
import { AssigneeControl } from "./AssigneeControl";
import { AuditPackageButton } from "./AuditPackageButton";
import { PayerSelect } from "./PayerSelect";

interface NoteToolsProps {
  note: NoteHeader;
  permissions: ReviewPermissions;
  onVisitType: (visitType: string) => void;
  onChanged: () => void;
}

const words = REVIEW_TEXT.tools;
const VOID_TEXT = {
  title: words.voidTitle,
  reason: words.voidReason,
  submit: words.confirm,
  cancel: words.keep,
  invalid: words.voidTooShort,
};

export function NoteTools({ note, permissions, onVisitType, onChanged }: NoteToolsProps) {
  const router = useRouter();
  const [voiding, setVoiding] = useState(false);
  const visitTypes: readonly string[] = VISIT_TYPES.includes(note.visit_type as (typeof VISIT_TYPES)[number])
    ? VISIT_TYPES
    : [note.visit_type, ...VISIT_TYPES];

  return (
    <section aria-label={words.label} className="flex flex-wrap items-center gap-3">
      <AssigneeControl note={note} />
      {permissions.editVisitType ? (
        <Select
          variant="filter"
          label={words.visitType}
          value={note.visit_type}
          options={visitTypes.map((visitType) => ({ value: visitType, label: visitType }))}
          onChange={onVisitType}
        />
      ) : null}
      {permissions.editVisitType ? <PayerSelect noteId={note.id} payer={note.payer} onChanged={onChanged} /> : null}
      <DefensePacketButton noteId={note.id} size="sm" />
      {permissions.auditPackage ? <AuditPackageButton noteId={note.id} /> : null}
      {permissions.voidNote ? (
        <Button size="sm" variant="plain" onClick={() => setVoiding(true)}>
          {words.void}
        </Button>
      ) : null}
      {voiding ? (
        <ReasonDialog
          destructive
          text={VOID_TEXT}
          minLength={VOID_REASON_MIN}
          maxLength={VOID_REASON_MAX}
          onClose={() => setVoiding(false)}
          onDone={() => router.push("/queue")}
          submit={(reason) => voidNotes([note.id], reason)}
        />
      ) : null}
    </section>
  );
}
