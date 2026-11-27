import { describe, expect, it } from "vitest";
import { NAV_ITEMS, isActive, navFor } from "@/components/shared/sidebar/navItems";
import type { Role } from "@/lib/api/types";
import { canDo, canOpenPath, canReach, canSearch, homeFor, idleMinutesFor } from "@/lib/roles";

const keysFor = (role: Role): string[] => navFor({ role, billing_only: false }).map((item) => item.key);
const BILLING_ONLY_ADMIN = { role: "admin", billing_only: true } as const;

describe("billing-only navigation", () => {
  it("offers a billing-only admin the plan screen and nothing else", () => {
    expect(navFor(BILLING_ONLY_ADMIN).map((item) => item.key)).toEqual(["plan"]);
    expect(homeFor(BILLING_ONLY_ADMIN)).toBe("/plan");
    expect(canReach(BILLING_ONLY_ADMIN, "plan")).toBe(true);
    expect(canReach(BILLING_ONLY_ADMIN, "help")).toBe(false);
    expect(canReach(BILLING_ONLY_ADMIN, "security")).toBe(false);
    expect(canSearch(BILLING_ONLY_ADMIN)).toBe(false);
  });

  it("opens only the plan path while billing-only, and every path once the plan is live", () => {
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/plan")).toBe(true);
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/today")).toBe(false);
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/notes/note-1")).toBe(false);
    expect(canOpenPath({ role: "admin", billing_only: false }, "/today")).toBe(true);
    expect(homeFor({ role: "admin", billing_only: false })).toBe("/today");
    expect(canSearch({ role: "admin", billing_only: false })).toBe(true);
  });
});

describe("role-based navigation", () => {
  it("shows each role only the screens its routes allow", () => {
    expect(keysFor("admin")).toEqual([
      "today",
      "upload",
      "queue",
      "compliance",
      "billing",
      "remittances",
      "training",
      "insights",
      "quality",
      "setup",
      "team",
      "plan",
      "security",
    ]);
    expect(keysFor("coder")).toEqual(["today", "upload", "queue", "training", "security"]);
    expect(keysFor("cdi")).toEqual(["today", "queue", "training", "security"]);
    expect(keysFor("compliance")).toEqual(["today", "queue", "compliance", "training", "insights", "quality", "security"]);
    expect(keysFor("biller")).toEqual(["today", "queue", "billing", "remittances", "training", "security"]);
    expect(keysFor("viewer")).toEqual(["today", "insights", "security"]);
    expect(keysFor("hq")).toEqual(["hqOverview", "hqPractices", "hqActivity", "hqDemos", "hqTeam", "hqSecurity"]);
  });

  it("mirrors the note action guards", () => {
    expect(canDo("cdi", "ask")).toBe(true);
    expect(canDo("cdi", "approve")).toBe(false);
    expect(canDo("biller", "decide")).toBe(false);
    expect(canDo("compliance", "complianceDecision")).toBe(true);
    expect(canDo("coder", "complianceDecision")).toBe(false);
    expect(canDo("coder", "retry")).toBe(true);
    expect(canDo("viewer", "flag")).toBe(false);
    expect(canDo("admin", "manageSecurity")).toBe(true);
    expect(canDo("coder", "manageSecurity")).toBe(false);
  });

  it("marks only the current screen as active", () => {
    const overview = NAV_ITEMS.find((item) => item.key === "hqOverview");
    const queue = NAV_ITEMS.find((item) => item.key === "queue");

    expect(overview && isActive(overview, "/hq")).toBe(true);
    expect(overview && isActive(overview, "/hq/practices")).toBe(false);
    expect(queue && isActive(queue, "/queue")).toBe(true);
    expect(queue && isActive(queue, "/queued")).toBe(false);
  });

  it("uses the practice inactivity limit, and fifteen minutes for HQ", () => {
    expect(idleMinutesFor("admin", 5)).toBe(5);
    expect(idleMinutesFor("coder", 30)).toBe(30);
    expect(idleMinutesFor("hq", null)).toBe(15);
    expect(idleMinutesFor("hq", 30)).toBe(15);
  });
});
