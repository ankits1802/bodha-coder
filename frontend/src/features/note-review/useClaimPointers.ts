"use client";

import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getClaimPointers, saveLinePointers } from "@/lib/api/pointers";
import type { OverrideChoice } from "@/lib/api/types";

export function useClaimPointers(noteId: string, claim: string[]) {
  const remote = useRemote(`pointers:${noteId}:${claim.join("|")}`, () => getClaimPointers(noteId));
  const action = useAction((code: string, pointers: string[], override: OverrideChoice) =>
    saveLinePointers(noteId, code, pointers, override),
  );

  return {
    state: remote.state,
    pending: action.pending,
    error: action.error,
    clearError: action.clearError,
    save: async (code: string, pointers: string[], override: OverrideChoice): Promise<boolean> => {
      const outcome = await action.run(code, pointers, override);
      if (outcome.ok) remote.replace(outcome.value);
      return outcome.ok;
    },
  };
}
