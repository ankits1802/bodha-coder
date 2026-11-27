"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { returnToCoder } from "@/lib/api/notes";
import type { ComplianceOutcome, ReturnReason, ReturnReasonChoice } from "@/lib/api/types";
import { RETURN_REASONS, RETURN_REASON_LABELS } from "@/lib/labels";
import { ReasonPicker } from "../reason-picker/ReasonPicker";
import { emptyReason, toReasonChoice } from "../reason-picker/reasonDraft";
import { SHARED_TEXT } from "../strings";

const WORDS = SHARED_TEXT.returnDialog;

interface ReturnDialogProps {
  noteId: string;
  onClose: () => void;
  onReturned: (outcome: ComplianceOutcome) => void;
}

export function ReturnDialog({ noteId, onClose, onReturned }: ReturnDialogProps) {
  const formId = useId();
  const [draft, setDraft] = useState(emptyReason<ReturnReason>());
  const [tried, setTried] = useState(false);
  const send = useAction((choice: ReturnReasonChoice) => returnToCoder(noteId, choice));

  async function submit(): Promise<void> {
    setTried(true);
    const choice = toReasonChoice(draft);
    if (!choice) return;
    const outcome = await send.run(choice);
    if (outcome.ok) onReturned(outcome.value);
  }

  const footer = (
    <>
      <Button onClick={onClose}>{WORDS.cancel}</Button>
      <Button type="submit" form={formId} variant="primary" pending={send.pending}>
        {WORDS.submit}
      </Button>
    </>
  );

  return (
    <Dialog open onClose={onClose} title={WORDS.title} footer={footer}>
      <form
        id={formId}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <ReasonPicker
          label={WORDS.label}
          reasons={RETURN_REASONS}
          labels={RETURN_REASON_LABELS}
          value={draft}
          showProblem={tried}
          autoFocus
          onChange={setDraft}
          onConfirm={() => void submit()}
        />
      </form>
      {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
    </Dialog>
  );
}
