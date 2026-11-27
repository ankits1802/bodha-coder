"use client";

import { useState } from "react";
import { ReasonDialog } from "@/components/shared/ReasonDialog";
import { Button } from "@/components/ui/Button";
import { ToneDot } from "@/components/ui/StatusDot";
import { restoreNote } from "@/lib/api/notes";
import type { VoidInfo } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { VOID_REASON_MAX, VOID_REASON_MIN } from "@/lib/validation";
import { REVIEW_TEXT } from "../strings";

interface VoidedLineProps {
  noteId: string;
  voided: VoidInfo;
  canRestore: boolean;
  onRestored: () => void;
}

const words = REVIEW_TEXT.voided;
const RESTORE_TEXT = {
  title: words.restoreTitle,
  reason: words.restoreReason,
  submit: words.restore,
  cancel: words.cancel,
  invalid: words.restoreTooShort,
};

export function VoidedLine({ noteId, voided, canRestore, onRestored }: VoidedLineProps) {
  const [restoring, setRestoring] = useState(false);
  const line = words.line(voided.by ?? words.someone, formatDateTime(voided.at), voided.reason ?? "");
  return (
    <section aria-label={words.label} className="flex flex-wrap items-center gap-3 text-body">
      <p className="m-0 flex min-w-0 items-center gap-2 text-subhead text-label-soft">
        <ToneDot tone="neutral" />
        <span className="min-w-0">{line}</span>
      </p>
      {canRestore ? (
        <Button size="sm" onClick={() => setRestoring(true)}>
          {words.restore}
        </Button>
      ) : null}
      {restoring ? (
        <ReasonDialog
          text={RESTORE_TEXT}
          minLength={VOID_REASON_MIN}
          maxLength={VOID_REASON_MAX}
          onClose={() => setRestoring(false)}
          onDone={() => {
            setRestoring(false);
            onRestored();
          }}
          submit={(reason) => restoreNote(noteId, reason)}
        />
      ) : null}
    </section>
  );
}
