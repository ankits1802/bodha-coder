import { canVoidNote } from "@/components/shared/noteStatus";
import type { NoteDetail, Role } from "@/lib/api/types";
import { canDo } from "@/lib/roles";
import { askableQuestions } from "./findings";

export interface ReviewPermissions {
  decide: boolean;
  approve: boolean;
  ask: boolean;
  flag: boolean;
  compliance: boolean;
  retry: boolean;
  reopen: boolean;
  remind: boolean;
  cancelRequest: boolean;
  voidNote: boolean;
  restore: boolean;
  editVisitType: boolean;
  seeRemovedComments: boolean;
  auditPackage: boolean;
}

const EDITABLE: readonly string[] = ["queued", "ready", "failed"];

export function reviewPermissions(role: Role | null | undefined, detail: NoteDetail): ReviewPermissions {
  const { status, lane } = detail.note;
  const ready = status === "ready";
  const inCompliance = lane === "compliance";
  return {
    decide: ready && canDo(role, "decide"),
    approve: ready && !inCompliance && canDo(role, "approve"),
    ask: ready && askableQuestions(detail.findings, detail.requests).length > 0 && canDo(role, "ask"),
    flag: ready && !inCompliance && canDo(role, "flag"),
    compliance: ready && inCompliance && canDo(role, "complianceDecision"),
    retry: status === "failed" && canDo(role, "retry"),
    reopen: status === "approved" && canDo(role, "approve"),
    remind: canDo(role, "ask") && detail.requests.some((request) => request.status === "sent"),
    cancelRequest: canDo(role, "ask") && detail.requests.some((request) => request.status === "sent"),
    voidNote: canVoidNote(role, status, detail.analysis !== null),
    restore: status === "voided" && canDo(role, "restoreNote"),
    editVisitType: EDITABLE.includes(status) && canDo(role, "manageNotes"),
    seeRemovedComments: canDo(role, "complianceDecision"),
    auditPackage: canDo(role, "complianceDecision"),
  };
}
