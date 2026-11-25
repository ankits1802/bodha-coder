import { describe, expect, it } from "vitest";
import { NAV_ITEMS, isActive, navFor } from "@/components/shared/sidebar/navItems";
import type { Role } from "@/lib/api/types";
import { canDo, idleMinutesFor } from "@/lib/roles";

const keysFor = (role: Role): string[] => navFor(role).map((item) => item.key);

describe("role-based navigation", () => {
  it("shows each role only the screens its routes allow", () => {
    expect(keysFor("admin")).toEqual(["today", "upload", "queue", "compliance", "billing", "insights", "setup", "team", "security"]);
    expect(keysFor("coder")).toEqual(["today", "upload", "queue", "security"]);
    expect(keysFor("cdi")).toEqual(["today", "queue", "security"]);
    expect(keysFor("compliance")).toEqual(["today", "queue", "compliance", "insights", "security"]);
    expect(keysFor("biller")).toEqual(["today", "queue", "billing", "security"]);
    expect(keysFor("viewer")).toEqual(["today", "insights", "security"]);
    expect(keysFor("hq")).toEqual(["hqOverview", "hqPractices", "hqActivity", "hqDemos"]);
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
