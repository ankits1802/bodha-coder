import { ASSIGNABLE_STATUSES, canVoidNote } from "@/components/shared/noteStatus";
import { urlFor } from "@/lib/api/client";
import type { Lane, LaneReason, QueueRow, User } from "@/lib/api/types";
import { notePath } from "@/lib/paths";
import { canDo } from "@/lib/roles";

export type Member = Pick<User, "id" | "role">;

export const NOTE_ROW_ATTRIBUTE = "data-note-id";

export interface BulkAbilities {
  approve: boolean;
  assign: boolean;
  void: boolean;
}

export function rowToToggle(rows: QueueRow[], member: Member, selectedIds: string[], focusedId: string | null): string | null {
  const focused = rows.find((row) => row.id === focusedId && isSelectable(row, member));
  if (focused) return focused.id;
  return rows.find((row) => isSelectable(row, member) && !selectedIds.includes(row.id))?.id ?? null;
}

export function isApprovable(row: QueueRow): boolean {
  return row.lane === "approve" && row.status === "ready" && row.lane_reason !== "returned";
}

export function isAwaitingProvider(row: QueueRow): boolean {
  return row.lane === "provider" && row.status === "ready" && row.lane_reason === "waiting_on_provider";
}

export function canOpen(row: QueueRow): boolean {
  return row.status === "ready" || row.status === "failed";
}

export function noteHref(noteId: string, lane: Lane | undefined, reason?: LaneReason): string {
  return urlFor(notePath(noteId), { lane, reason });
}

export function patientName(row: QueueRow): string {
  return row.patient_name ?? row.file_name;
}

function canAssign(row: QueueRow, member: Member): boolean {
  if (!canDo(member.role, "assign") || !ASSIGNABLE_STATUSES.includes(row.status)) return false;
  return canDo(member.role, "assignAnyone") || row.assigned_to === null || row.assigned_to === member.id;
}

export function rowAbilities(row: QueueRow, member: Member): BulkAbilities {
  return {
    approve: canDo(member.role, "approve") && isApprovable(row),
    assign: canAssign(row, member),
    void: canVoidNote(member.role, row.status, row.status === "ready"),
  };
}

export function isSelectable(row: QueueRow, member: Member): boolean {
  const abilities = rowAbilities(row, member);
  return abilities.approve || abilities.assign || abilities.void;
}

export function bulkAbilities(rows: QueueRow[], member: Member): BulkAbilities {
  const each = rows.map((row) => rowAbilities(row, member));
  const every = (key: keyof BulkAbilities) => each.length > 0 && each.every((abilities) => abilities[key]);
  return { approve: every("approve"), assign: every("assign"), void: every("void") };
}

export function selectsRows(member: Member): boolean {
  return canDo(member.role, "approve") || canDo(member.role, "assign") || canDo(member.role, "manageNotes");
}
