"use client";

import { usePlanStatus } from "@/hooks/usePlanStatus";
import { usePracticeSetup } from "@/hooks/usePracticeSetup";
import { useTeam } from "@/hooks/useTeam";
import type { PracticeSetup } from "@/lib/api/types";
import { checklistSteps, isChecklistShown, type ChecklistStep } from "./checklistModel";

export type FirstRunStatus = "off" | "loading" | "error" | "ready";

export interface FirstRun {
  status: FirstRunStatus;
  error: string | null;
  setup: PracticeSetup | null;
  steps: ChecklistStep[];
  shown: boolean;
  retry: () => void;
  reloadSetup: () => void;
  reloadTeam: () => void;
}

export function useFirstRun(enabled: boolean): FirstRun {
  const setup = usePracticeSetup(enabled);
  const team = useTeam(enabled);
  const plan = usePlanStatus(enabled);
  const states = [setup.state, team.state, plan.state];
  const failed = states.find((state) => state.status === "error");
  const base = {
    retry: () => [setup, team, plan].forEach((remote) => remote.reload()),
    reloadSetup: setup.reload,
    reloadTeam: team.reload,
  };
  if (!enabled) return { ...base, status: "off", error: null, setup: null, steps: [], shown: false };
  if (failed?.status === "error") return { ...base, status: "error", error: failed.error, setup: null, steps: [], shown: false };
  if (setup.state.status !== "success" || team.state.status !== "success" || plan.state.status !== "success") {
    return { ...base, status: "loading", error: null, setup: null, steps: [], shown: false };
  }
  const steps = checklistSteps(setup.state.data, team.state.data, plan.state.data);
  return { ...base, status: "ready", error: null, setup: setup.state.data, steps, shown: isChecklistShown(setup.state.data, steps) };
}
