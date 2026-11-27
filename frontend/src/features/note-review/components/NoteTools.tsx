"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { deleteNotes } from "@/lib/api/notes";
import type { NoteHeader } from "@/lib/api/types";
import { VISIT_TYPES } from "@/lib/labels";
import type { ReviewPermissions } from "../permissions";
import { REVIEW_TEXT } from "../strings";
import { AssigneeControl } from "./AssigneeControl";
import { AuditPackageButton } from "./AuditPackageButton";
import { DefensePacketButton } from "@/components/shared/defense/DefensePacketButton";
import { PayerSelect } from "./PayerSelect";

interface NoteToolsProps {
  note: NoteHeader;
  permissions: ReviewPermissions;
  onVisitType: (visitType: string) => void;
  onChanged: () => void;
}

export function NoteTools({ note, permissions, onVisitType, onChanged }: NoteToolsProps) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const remove = useAction(() => deleteNotes([note.id]));
  const words = REVIEW_TEXT.tools;
  const visitTypes: readonly string[] = VISIT_TYPES.includes(note.visit_type as (typeof VISIT_TYPES)[number])
    ? VISIT_TYPES
    : [note.visit_type, ...VISIT_TYPES];

  async function confirmDelete(): Promise<void> {
    if ((await remove.run()).ok) router.push("/queue");
  }

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
      {permissions.deleteNote ? (
        <Button size="sm" variant="plain" onClick={() => setConfirming(true)}>
          {words.delete}
        </Button>
      ) : null}
      <Dialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={words.deleteTitle}
        description={words.deleteDescription}
        footer={
          <>
            <Button onClick={() => setConfirming(false)}>{words.keep}</Button>
            <Button variant="danger" onClick={() => void confirmDelete()} pending={remove.pending}>
              {words.confirm}
            </Button>
          </>
        }
      >
        {remove.error ? <InlineAlert tone="bad">{remove.error}</InlineAlert> : null}
      </Dialog>
    </section>
  );
}
