"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { approveNotes, assignNotes, deleteNotes, remindProvider, retryFailedNotes } from "@/lib/api/notes";
import { formatCount } from "@/lib/format";
import { QUEUE_TEXT } from "./strings";

export interface QueueActions {
  approveSelected: (noteIds: string[]) => Promise<void>;
  approving: boolean;
  assignSelected: (noteIds: string[], userId: string | null) => Promise<boolean>;
  assigning: boolean;
  assignError: string | null;
  deleteSelected: (noteIds: string[]) => Promise<boolean>;
  deleting: boolean;
  deleteError: string | null;
  clearDialogErrors: () => void;
  remindOne: (noteId: string) => Promise<void>;
  remindingId: string | null;
  retryFailed: () => Promise<void>;
  retrying: boolean;
  notice: string | null;
  error: string | null;
}

export function useQueueActions(onChanged: () => void): QueueActions {
  const approve = useAction(approveNotes);
  const assign = useAction(assignNotes);
  const remove = useAction(deleteNotes);
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
    onChanged();
  }

  async function assignSelected(noteIds: string[], userId: string | null): Promise<boolean> {
    setNotice(null);
    const outcome = await assign.run(noteIds, userId);
    if (!outcome.ok) return false;
    setNotice(QUEUE_TEXT.assignedNotice(formatCount(outcome.value.assigned.length)));
    onChanged();
    return true;
  }

  async function deleteSelected(noteIds: string[]): Promise<boolean> {
    setNotice(null);
    const outcome = await remove.run(noteIds);
    if (!outcome.ok) return false;
    setNotice(QUEUE_TEXT.deletedNotice(formatCount(outcome.value.deleted.length)));
    onChanged();
    return true;
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
    onChanged();
  }

  return {
    approveSelected,
    approving: approve.pending,
    assignSelected,
    assigning: assign.pending,
    assignError: assign.error,
    deleteSelected,
    deleting: remove.pending,
    deleteError: remove.error,
    clearDialogErrors: () => {
      assign.clearError();
      remove.clearError();
    },
    remindOne,
    remindingId,
    retryFailed,
    retrying: retry.pending,
    notice,
    error: approve.error ?? remind.error ?? retry.error,
  };
}
