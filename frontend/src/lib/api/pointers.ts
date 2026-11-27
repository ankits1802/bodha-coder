import { request } from "./client";
import type { ClaimPointers } from "./types";

const pointersPath = (noteId: string): string => `/api/notes/${encodeURIComponent(noteId)}/pointers`;

export function getClaimPointers(noteId: string): Promise<ClaimPointers> {
  return request<ClaimPointers>(pointersPath(noteId));
}

export function saveLinePointers(noteId: string, code: string, pointers: string[]): Promise<ClaimPointers> {
  return request<ClaimPointers>(pointersPath(noteId), { method: "PUT", body: { lines: [{ code, pointers }] } });
}
