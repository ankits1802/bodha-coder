"use client";

import { useRemote } from "@/hooks/useRemote";
import { getClaimChecks } from "@/lib/api/claimChecks";

export function useClaimChecks(noteId: string, claim: string[]) {
  return useRemote(`claim-checks:${noteId}:${claim.join(",")}`, () => getClaimChecks(noteId));
}
