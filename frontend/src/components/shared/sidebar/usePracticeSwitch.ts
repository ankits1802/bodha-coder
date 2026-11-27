"use client";

import { useAction } from "@/hooks/useAction";
import { switchPractice } from "@/lib/api/auth";
import { enterPractice } from "@/lib/session/practiceEntry";

export function usePracticeSwitch(currentId: string | null) {
  const switching = useAction(switchPractice);

  async function choose(practiceId: string): Promise<void> {
    if (practiceId === currentId) return;
    const outcome = await switching.run(practiceId);
    if (outcome.ok) enterPractice(outcome.value);
  }

  return { choose, pending: switching.pending, error: switching.error };
}
