"use client";

import { ReasonDialog } from "@/components/shared/ReasonDialog";
import { decideCompliance, flagNote } from "@/lib/api/notes";
import type { Finding, NoteDetail } from "@/lib/api/types";
import { COMPLIANCE_REASON_MAX } from "@/lib/validation";
import { REVIEW_TEXT } from "../strings";
import { AskProviderDialog } from "./AskProviderDialog";

export type OpenDialog = "ask" | "flag" | "keep" | null;

interface ReviewDialogsProps {
  open: OpenDialog;
  detail: NoteDetail;
  questions: Finding[];
  onClose: () => void;
  onChanged: () => void;
  onApproved: () => void;
}

const FLAG_TEXT = { ...REVIEW_TEXT.flagDialog, invalid: REVIEW_TEXT.flagDialog.tooShort };
const KEEP_TEXT = { ...REVIEW_TEXT.keepDialog, invalid: REVIEW_TEXT.keepDialog.required };
const FLAG_MAX = 2000;

export function ReviewDialogs({ open, detail, questions, onClose, onChanged, onApproved }: ReviewDialogsProps) {
  const noteId = detail.note.id;
  if (open === "ask") return <AskProviderDialog detail={detail} questions={questions} onClose={onClose} onSent={onChanged} />;
  if (open === "flag") {
    return <ReasonDialog text={FLAG_TEXT} minLength={3} maxLength={FLAG_MAX} onClose={onClose} onDone={onChanged} submit={(reason) => flagNote(noteId, reason)} />;
  }
  if (open === "keep") {
    return (
      <ReasonDialog
        text={KEEP_TEXT}
        minLength={1}
        maxLength={COMPLIANCE_REASON_MAX}
        onClose={onClose}
        onDone={onApproved}
        submit={(reason) => decideCompliance(noteId, "keep", reason)}
      />
    );
  }
  return null;
}
