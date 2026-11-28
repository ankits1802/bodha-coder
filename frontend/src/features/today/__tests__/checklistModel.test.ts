import { describe, expect, it } from "vitest";
import { planStatus } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { canHide, checklistSteps, doneCount, isChecklistShown, nextStep, RECOMMENDED_SECURITY, STEP_LINKS } from "../checklist/checklistModel";
import { setupWith, teamOf } from "./firstRunFixtures";

describe("first-day checklist", () => {
  it("starts with every step open for a new practice on a trial", () => {
    const steps = checklistSteps(setupWith(), teamOf(1), planStatus());
    expect(steps.map((step) => [step.key, step.done])).toEqual([
      ["providers", false],
      ["payers", false],
      ["checks", false],
      ["invite", false],
      ["security", false],
      ["plan", false],
    ]);
    expect(nextStep(steps)).toBe("providers");
    expect(canHide(steps)).toBe(false);
  });

  it("reads each step from setup, the team and the plan", () => {
    const setup = setupWith({ providers: true, payer: true, checks: true, security: true });
    const steps = checklistSteps(setup, teamOf(2), planStatus({ standing: "active", plan: "professional" }));
    expect(doneCount(steps)).toBe(6);
    expect(isChecklistShown(setup, steps)).toBe(false);
    expect(nextStep(steps)).toBeNull();
  });

  it("counts a trial, an ended or a canceled plan as not chosen, and a managed plan as chosen", () => {
    const plan = (standing: "trial" | "ended" | "canceled" | "managed" | "past_due") =>
      checklistSteps(setupWith(), teamOf(1), planStatus({ standing })).find((step) => step.key === "plan")?.done;
    expect([plan("trial"), plan("ended"), plan("canceled"), plan("managed"), plan("past_due")]).toEqual([false, false, false, true, true]);
  });

  it("can be hidden once providers are in, and stays hidden after that", () => {
    const steps = checklistSteps(setupWith({ providers: true }), teamOf(1), planStatus());
    expect(canHide(steps)).toBe(true);
    expect(nextStep(steps)).toBe("payers");
    expect(isChecklistShown(setupWith({ providers: true, dismissed: true }), steps)).toBe(false);
  });

  it("links each step to its place in Settings and recommends two-step for everyone", () => {
    expect(STEP_LINKS.providers).toBe("/settings/setup?section=providers");
    expect(STEP_LINKS.checks).toBe("/settings/setup?section=checks");
    expect(STEP_LINKS.invite).toBe("/settings/team");
    expect(STEP_LINKS.security).toBe("/settings/security");
    expect(STEP_LINKS.plan).toBe("/settings/plan");
    expect(RECOMMENDED_SECURITY).toEqual({
      mfa_roles: ["admin", "coder", "cdi", "compliance", "biller", "viewer"],
      idle_minutes: 10_080,
      access_log_years: 7,
    });
  });
});
