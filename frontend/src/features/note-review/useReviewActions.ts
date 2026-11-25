"use client";

import { useAction } from "@/hooks/useAction";
import { approveNote, decideCompliance, getNoteDocument, remindProvider, retryNote } from "@/lib/api/notes";
import type { ComplianceDecision } from "@/lib/api/types";
import { openDocument } from "@/lib/openDocument";

interface ReviewCallbacks {
  approved: () => void;
  changed: () => void;
}

export function useReviewActions(noteId: string, callbacks: ReviewCallbacks) {
  const approve = useAction(() => approveNote(noteId));
  const compliance = useAction((decision: ComplianceDecision, reason: string | null) =>
    decideCompliance(noteId, decision, reason),
  );
  const retry = useAction(() => retryNote(noteId));
  const remind = useAction(() => remindProvider(noteId));
  const pdf = useAction(() => openDocument(() => getNoteDocument(noteId)));

  return {
    pending: approve.pending || compliance.pending || retry.pending,
    error: approve.error ?? compliance.error ?? retry.error ?? pdf.error,
    remindError: remind.error,
    remindPending: remind.pending,
    pdfPending: pdf.pending,
    approve: async () => {
      if ((await approve.run()).ok) callbacks.approved();
    },
    decideCompliance: async (decision: ComplianceDecision, reason: string | null) => {
      const outcome = await compliance.run(decision, reason);
      if (!outcome.ok) return outcome;
      if (outcome.value.status === "approved") callbacks.approved();
      else callbacks.changed();
      return outcome;
    },
    retry: async () => {
      if ((await retry.run()).ok) callbacks.changed();
    },
    remind: () => remind.run(),
    openPdf: () => void pdf.run(),
  };
}

export type ReviewActions = ReturnType<typeof useReviewActions>;
