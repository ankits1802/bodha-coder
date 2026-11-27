"use client";

import { useSignatureGate } from "@/components/shared/signature/useSignatureGate";
import { useAction } from "@/hooks/useAction";
import {
  approveNote,
  cancelRequest,
  changeVisitType,
  decideCompliance,
  getNoteDocument,
  remindProvider,
  reopenNote,
  retryNote,
} from "@/lib/api/notes";
import type { ComplianceDecision } from "@/lib/api/types";
import { openDocument } from "@/lib/openDocument";

interface ReviewCallbacks {
  approved: () => void;
  moveOn: () => void;
  changed: () => void;
}

export function useReviewActions(noteId: string, callbacks: ReviewCallbacks) {
  const signatureGate = useSignatureGate();
  const approve = useAction(signatureGate.gated(() => approveNote(noteId)));
  const compliance = useAction(
    signatureGate.gated((decision: ComplianceDecision, reason: string | null) => decideCompliance(noteId, decision, reason)),
  );
  const retry = useAction(() => retryNote(noteId));
  const reopen = useAction(() => reopenNote(noteId));
  const cancel = useAction(() => cancelRequest(noteId));
  const visit = useAction((visitType: string) => changeVisitType(noteId, visitType));
  const remind = useAction(() => remindProvider(noteId));
  const pdf = useAction(() => openDocument(() => getNoteDocument(noteId)));

  return {
    pending: approve.pending || compliance.pending || retry.pending || reopen.pending || visit.pending,
    error: approve.error ?? compliance.error ?? retry.error ?? reopen.error ?? visit.error ?? cancel.error ?? pdf.error,
    cancelPending: cancel.pending,
    remindError: remind.error,
    remindPending: remind.pending,
    pdfPending: pdf.pending,
    signatureGate,
    approve: async () => {
      if ((await approve.run()).ok) callbacks.approved();
    },
    decideCompliance: async (decision: ComplianceDecision, reason: string | null) => {
      const outcome = await compliance.run(decision, reason);
      if (!outcome.ok) return outcome;
      if (outcome.value.status === "approved") callbacks.moveOn();
      else callbacks.changed();
      return outcome;
    },
    retry: async () => {
      if ((await retry.run()).ok) callbacks.changed();
    },
    reopen: async () => {
      if ((await reopen.run()).ok) callbacks.changed();
    },
    remind: () => remind.run(),
    cancelRequest: async () => {
      if ((await cancel.run()).ok) callbacks.changed();
    },
    changeVisitType: async (visitType: string) => {
      if ((await visit.run(visitType)).ok) callbacks.changed();
    },
    openPdf: () => void pdf.run(),
  };
}

export type ReviewActions = ReturnType<typeof useReviewActions>;
