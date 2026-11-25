"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { approveNotes, remindProvider, retryFailedNotes } from "@/lib/api/notes";
import { formatCount } from "@/lib/format";
import { QUEUE_TEXT } from "./strings";

export interface QueueActions {
  approveSelected: (noteIds: string[]) => Promise<void>;
  approving: boolean;
  remindOne: (noteId: string) => Promise<void>;
  remindingId: string | null;
  retryFailed: () => Promise<void>;
  retrying: boolean;
  notice: string | null;
  error: string | null;
}

export function useQueueActions(onApproved: () => void): QueueActions {
  const approve = useAction(approveNotes);
  const remind = useAction(remindProvider);
  const retry = useAction(retryFailedNotes);
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

  async function retryFailed(): Promise<void> {
    setNotice(null);
    const outcome = await retry.run(null);
    if (!outcome.ok) return;
    setNotice(QUEUE_TEXT.readingAgain(formatCount(outcome.value.queued.length)));
    onApproved();
  }

  return {
    approveSelected,
    approving: approve.pending,
    remindOne,
    remindingId,
    retryFailed,
    retrying: retry.pending,
    notice,
    error: approve.error ?? remind.error ?? retry.error,
  };
}
