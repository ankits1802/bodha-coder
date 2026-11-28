import type { PlanStanding, PlanStatus, PracticeSetup, SecuritySettings, TeamList } from "@/lib/api/types";
import { SECURITY_SETTINGS_PATH, TEAM_PATH, setupSectionPath } from "@/lib/paths";
import { PLAN_PATH, PRACTICE_ROLES } from "@/lib/roles";

export type StepKey = "providers" | "payers" | "checks" | "invite" | "security" | "plan";

export interface ChecklistStep {
  key: StepKey;
  done: boolean;
}

export const STEP_ORDER: readonly StepKey[] = ["providers", "payers", "checks", "invite", "security", "plan"];

const PLAN_CHOSEN: readonly PlanStanding[] = ["active", "canceling", "past_due", "managed"];

export const RECOMMENDED_SECURITY: SecuritySettings = { mfa_roles: [...PRACTICE_ROLES], idle_minutes: 10_080, access_log_years: 7 };

export const STEP_LINKS: Readonly<Record<StepKey, string>> = {
  providers: setupSectionPath("providers"),
  payers: setupSectionPath("payers"),
  checks: setupSectionPath("checks"),
  invite: TEAM_PATH,
  security: SECURITY_SETTINGS_PATH,
  plan: PLAN_PATH,
};

export function checklistSteps(setup: PracticeSetup, team: TeamList, plan: PlanStatus): ChecklistStep[] {
  const done: Record<StepKey, boolean> = {
    providers: setup.sections.providers.complete,
    payers: setup.payers.some((payer) => payer.active),
    checks: setup.first_run.checks,
    invite: team.members.length > 1,
    security: setup.first_run.security,
    plan: PLAN_CHOSEN.includes(plan.standing),
  };
  return STEP_ORDER.map((key) => ({ key, done: done[key] }));
}

export function doneCount(steps: readonly ChecklistStep[]): number {
  return steps.filter((step) => step.done).length;
}

export function isChecklistShown(setup: PracticeSetup, steps: readonly ChecklistStep[]): boolean {
  return !setup.first_run.dismissed && steps.some((step) => !step.done);
}

export function canHide(steps: readonly ChecklistStep[]): boolean {
  return steps.some((step) => step.key === "providers" && step.done);
}

export function nextStep(steps: readonly ChecklistStep[]): StepKey | null {
  return steps.find((step) => !step.done)?.key ?? null;
}
