import { request } from "./client";
import type { ClaimPointers, OverrideChoice } from "./types";

const pointersPath = (noteId: string): string => `/api/notes/${encodeURIComponent(noteId)}/pointers`;

export function getClaimPointers(noteId: string): Promise<ClaimPointers> {
  return request<ClaimPointers>(pointersPath(noteId));
}

export function saveLinePointers(
  noteId: string,
  code: string,
  pointers: string[],
  reason: OverrideChoice,
): Promise<ClaimPointers> {
  return request<ClaimPointers>(pointersPath(noteId), { method: "PUT", body: { lines: [{ code, pointers }], reason } });
}
