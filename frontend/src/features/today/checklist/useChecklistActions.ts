"use client";

import { useAction } from "@/hooks/useAction";
import { refreshSession } from "@/lib/api/client";
import { dismissFirstRun, saveChecks, saveSecurity } from "@/lib/api/practice";
import type { Checks } from "@/lib/api/types";
import { RECOMMENDED_SECURITY } from "./checklistModel";

async function applyRecommendedSecurity(): Promise<void> {
  await saveSecurity(RECOMMENDED_SECURITY);
  await refreshSession();
}

export function useChecklistActions(onSetupChanged: () => void) {
  const checks = useAction(saveChecks);
  const security = useAction(applyRecommendedSecurity);
  const hide = useAction(dismissFirstRun);

  async function run<A extends unknown[]>(action: { run: (...args: A) => Promise<{ ok: boolean }> }, ...args: A): Promise<void> {
    const outcome = await action.run(...args);
    if (outcome.ok) onSetupChanged();
  }

  return {
    saveChecks: (draft: Checks) => void run(checks, draft),
    applyRecommended: () => void run(security),
    hide: () => void run(hide),
    pending: { checks: checks.pending, security: security.pending, hide: hide.pending },
    error: checks.error ?? security.error ?? hide.error,
  };
}
