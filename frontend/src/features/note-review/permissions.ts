import type { NoteDetail, Role } from "@/lib/api/types";
import { canDo, canUse } from "@/lib/roles";
import { openQuestions } from "./findings";

export interface ReviewPermissions {
  decide: boolean;
  approve: boolean;
  ask: boolean;
  flag: boolean;
  compliance: boolean;
  retry: boolean;
  remind: boolean;
  readPlaces: boolean;
}

export function reviewPermissions(role: Role | null | undefined, detail: NoteDetail): ReviewPermissions {
  const { status, lane } = detail.note;
  const ready = status === "ready";
  const inCompliance = lane === "compliance";
  return {
    decide: ready && canDo(role, "decide"),
    approve: ready && !inCompliance && canDo(role, "approve"),
    ask: ready && openQuestions(detail.findings).length > 0 && canDo(role, "ask"),
    flag: ready && !inCompliance && canDo(role, "flag"),
    compliance: ready && inCompliance && canDo(role, "complianceDecision"),
    retry: status === "failed" && canDo(role, "retry"),
    remind: canDo(role, "ask") && detail.requests.some((request) => request.status === "sent"),
    readPlaces: canUse(role, "upload"),
  };
}
