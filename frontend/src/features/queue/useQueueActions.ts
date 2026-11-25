"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { approveNotes, remindProvider } from "@/lib/api/notes";
import { formatCount } from "@/lib/format";
import { QUEUE_TEXT } from "./strings";

export interface QueueActions {
  approveSelected: (noteIds: string[]) => Promise<void>;
  approving: boolean;
  remindOne: (noteId: string) => Promise<void>;
  remindingId: string | null;
  notice: string | null;
  error: string | null;
}

export function useQueueActions(onApproved: () => void): QueueActions {
  const approve = useAction(approveNotes);
  const remind = useAction(remindProvider);
  const [remindingId, setRemindingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function approveSelected(noteIds: string[]): Promise<void> {
    setNotice(null);
    remind.clearError();
    const outcome = await approve.run(noteIds);
    if (!outcome.ok) return;
    setNotice(QUEUE_TEXT.approved(formatCount(outcome.value.approved.length)));
    onApproved();
  }

  async function remindOne(noteId: string): Promise<void> {
    setNotice(null);
    approve.clearError();
    setRemindingId(noteId);
    const outcome = await remind.run(noteId);
    setRemindingId(null);
    if (outcome.ok) setNotice(QUEUE_TEXT.reminded);
  }

  return {
    approveSelected,
    approving: approve.pending,
    remindOne,
    remindingId,
    notice,
    error: approve.error ?? remind.error,
  };
}
