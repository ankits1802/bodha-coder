export const REASON_NOTE_MAX = 500;
export const OTHER_REASON = "other";

export interface ReasonDraft<R extends string> {
  reason: R | null;
  note: string;
}

export interface ReasonChoice<R extends string> {
  reason: R;
  note: string | null;
}

export type ReasonProblem = "choose" | "note" | "long";

export function emptyReason<R extends string>(): ReasonDraft<R> {
  return { reason: null, note: "" };
}

export function reasonAtKey<R extends string>(reasons: readonly R[], key: string): R | null {
  if (!/^[1-9]$/.test(key)) return null;
  return reasons[Number.parseInt(key, 10) - 1] ?? null;
}

export function reasonProblem<R extends string>(draft: ReasonDraft<R>): ReasonProblem | null {
  if (draft.reason === null) return "choose";
  const note = draft.note.trim();
  if (note.length > REASON_NOTE_MAX) return "long";
  if (draft.reason === OTHER_REASON && note === "") return "note";
  return null;
}

export function toReasonChoice<R extends string>(draft: ReasonDraft<R>): ReasonChoice<R> | null {
  if (draft.reason === null || reasonProblem(draft) !== null) return null;
  const note = draft.note.trim();
  return { reason: draft.reason, note: note === "" ? null : note };
}
