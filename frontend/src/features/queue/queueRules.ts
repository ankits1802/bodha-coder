import type { Lane, QueueRow } from "@/lib/api/types";
import { LANE_ORDER } from "@/lib/labels";

export const AWAITING_PROVIDER_HEADLINE = "Waiting on provider";

export function isLane(value: string | null): value is Lane {
  return value !== null && (LANE_ORDER as readonly string[]).includes(value);
}

export function isSelectable(row: QueueRow): boolean {
  return row.lane === "approve" && row.status === "ready";
}

export function isAwaitingProvider(row: QueueRow): boolean {
  return row.lane === "provider" && row.status === "ready" && row.headline === AWAITING_PROVIDER_HEADLINE;
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
