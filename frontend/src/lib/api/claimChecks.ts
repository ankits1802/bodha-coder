import { request } from "./client";
import type { ClaimChecks } from "./types";

export function getClaimChecks(noteId: string): Promise<ClaimChecks> {
  return request<ClaimChecks>(`/api/notes/${encodeURIComponent(noteId)}/claim-checks`);
}
