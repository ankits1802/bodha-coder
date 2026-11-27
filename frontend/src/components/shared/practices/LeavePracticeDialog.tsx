"use client";

import { useAction } from "@/hooks/useAction";
import { leavePractice } from "@/lib/api/auth";
import { refreshSession } from "@/lib/api/client";
import type { PracticeChoice } from "@/lib/api/types";
import { signOut } from "@/lib/session/signOut";
import { ConfirmDialog } from "../ConfirmDialog";
import { PRACTICE_TEXT } from "./strings";

async function leave(practice: PracticeChoice, current: boolean): Promise<void> {
  await leavePractice(practice.id);
  if (current) await signOut();
  else await refreshSession();
}

interface LeavePracticeDialogProps {
  practice: PracticeChoice | null;
  currentId: string | null;
  onClose: () => void;
}

export function LeavePracticeDialog({ practice, currentId, onClose }: LeavePracticeDialogProps) {
  const action = useAction(leave);

  async function confirm(): Promise<void> {
    if (!practice) return;
    const outcome = await action.run(practice, practice.id === currentId);
    if (outcome.ok) onClose();
  }

  return (
    <ConfirmDialog
      open={practice !== null}
      title={practice ? PRACTICE_TEXT.confirmTitle(practice.name) : ""}
      confirmLabel={PRACTICE_TEXT.leave}
      cancelLabel={PRACTICE_TEXT.cancel}
      destructive
      pending={action.pending}
      error={action.error}
      onConfirm={() => void confirm()}
      onClose={() => {
        action.clearError();
        onClose();
      }}
    />
  );
}
