"use client";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { useAction } from "@/hooks/useAction";
import { HQ_TEXT } from "../strings";
import { confirmWords, isTypedAction, runPracticeAction, type PracticeAction } from "./practiceActions";
import { TypedNameDialog } from "./TypedNameDialog";

interface PracticeActionDialogProps {
  action: PracticeAction;
  onDone: (notice: string | null) => void;
  onClose: () => void;
}

export function PracticeActionDialog({ action, onDone, onClose }: PracticeActionDialogProps) {
  const run = useAction(runPracticeAction);

  async function confirm(typedName = ""): Promise<void> {
    const outcome = await run.run(action, typedName);
    if (outcome.ok) onDone(outcome.value);
  }

  if (isTypedAction(action.kind)) {
    return (
      <TypedNameDialog
        kind={action.kind}
        practice={action.practice}
        pending={run.pending}
        error={run.error}
        onConfirm={(typedName) => void confirm(typedName)}
        onClose={onClose}
      />
    );
  }
  const words = confirmWords(action);
  return (
    <ConfirmDialog
      open
      title={words.title}
      description={words.description}
      confirmLabel={words.confirm}
      cancelLabel={HQ_TEXT.practices.confirm.cancel}
      destructive={words.destructive}
      pending={run.pending}
      error={run.error}
      onConfirm={() => void confirm()}
      onClose={onClose}
    />
  );
}
