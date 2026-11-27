import { ASSIGNABLE_STATUSES, DELETABLE_STATUSES } from "@/components/shared/noteStatus";
import type { Lane, LaneReason, QueueRow, User } from "@/lib/api/types";
import { LANE_ORDER } from "@/lib/labels";
import { canDo } from "@/lib/roles";

export type Member = Pick<User, "id" | "role">;

export const NOTE_ROW_ATTRIBUTE = "data-note-id";

export interface BulkAbilities {
  approve: boolean;
  assign: boolean;
  remove: boolean;
}

const LANE_REASONS: Record<LaneReason, true> = {
  flagged: true,
  levels_too_high: true,
  audit_risk: true,
  waiting_on_provider: true,
  code_changes: true,
  questions: true,
  matches: true,
};

export function isLane(value: string | null): value is Lane {
  return value !== null && (LANE_ORDER as readonly string[]).includes(value);
}

export function isLaneReason(value: string | null): value is LaneReason {
  return value !== null && Object.hasOwn(LANE_REASONS, value);
}

export function rowToToggle(rows: QueueRow[], member: Member, selectedIds: string[], focusedId: string | null): string | null {
  const focused = rows.find((row) => row.id === focusedId && isSelectable(row, member));
  if (focused) return focused.id;
  return rows.find((row) => isSelectable(row, member) && !selectedIds.includes(row.id))?.id ?? null;
}

export function isApprovable(row: QueueRow): boolean {
  return row.lane === "approve" && row.status === "ready";
}

export function isAwaitingProvider(row: QueueRow): boolean {
  return row.lane === "provider" && row.status === "ready" && row.lane_reason === "waiting_on_provider";
}

export function canOpen(row: QueueRow): boolean {
  return row.status === "ready" || row.status === "failed";
}

export function noteHref(noteId: string, lane: Lane | undefined): string {
  const path = `/notes/${encodeURIComponent(noteId)}`;
  return lane ? `${path}?lane=${lane}` : path;
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
    remove: canDo(member.role, "manageNotes") && DELETABLE_STATUSES.includes(row.status),
  };
}

export function isSelectable(row: QueueRow, member: Member): boolean {
  const abilities = rowAbilities(row, member);
  return abilities.approve || abilities.assign || abilities.remove;
}

export function bulkAbilities(rows: QueueRow[], member: Member): BulkAbilities {
  const each = rows.map((row) => rowAbilities(row, member));
  const every = (key: keyof BulkAbilities) => each.length > 0 && each.every((abilities) => abilities[key]);
  return { approve: every("approve"), assign: every("assign"), remove: every("remove") };
}

export function selectsRows(member: Member): boolean {
  return canDo(member.role, "approve") || canDo(member.role, "assign") || canDo(member.role, "manageNotes");
}
