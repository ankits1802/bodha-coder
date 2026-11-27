import type { QueueRow, Role, TodaySummary } from "@/lib/api/types";

export type StartKind = "review" | "questions" | "compliance" | "billing";

export interface TodayStart {
  kind: StartKind;
  href: string;
  noteId: string | null;
}

type Summary = Pick<TodaySummary, "next_up" | "waiting" | "batches">;

export const START_LANE = "coder";
const LANE_PATH = `/queue?lane=${START_LANE}`;
const MY_WORK_PATH = "/queue?assigned=me";
const FIXED: Readonly<Record<Exclude<StartKind, "review">, string>> = {
  questions: "/queue?lane=provider&reason=questions",
  compliance: "/compliance",
  billing: "/billing",
};

function noteStart(row: QueueRow): TodayStart {
  return { kind: "review", href: `/notes/${encodeURIComponent(row.id)}?lane=${START_LANE}`, noteId: row.id };
}

function fixedStart(kind: Exclude<StartKind, "review">): TodayStart {
  return { kind, href: FIXED[kind], noteId: null };
}

export function hasNotes(summary: Pick<TodaySummary, "waiting" | "batches">): boolean {
  return summary.waiting > 0 || summary.batches.length > 0;
}

export function myNextNote(rows: readonly QueueRow[], userId: string): QueueRow | null {
  return rows.find((row) => row.assigned_to === userId) ?? rows.find((row) => row.assigned_to === null) ?? null;
}

function coderStart(summary: Summary, userId: string): TodayStart {
  const next = myNextNote(summary.next_up, userId);
  return next ? noteStart(next) : { kind: "review", href: MY_WORK_PATH, noteId: null };
}

function adminStart(summary: Summary): TodayStart | null {
  if (!hasNotes(summary)) return null;
  const first = summary.next_up[0];
  return first ? noteStart(first) : { kind: "review", href: LANE_PATH, noteId: null };
}

const STARTS: Partial<Record<Role, (summary: Summary, userId: string) => TodayStart | null>> = {
  coder: coderStart,
  admin: adminStart,
  cdi: () => fixedStart("questions"),
  compliance: () => fixedStart("compliance"),
  biller: () => fixedStart("billing"),
};

export function startFor(role: Role, summary: Summary, userId: string): TodayStart | null {
  return STARTS[role]?.(summary, userId) ?? null;
}
