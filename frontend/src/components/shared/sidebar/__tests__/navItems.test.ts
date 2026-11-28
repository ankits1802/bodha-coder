import { describe, expect, it } from "vitest";
import { NAV_ITEMS, activeTab, isActive, navFor, navItemFor } from "@/components/shared/sidebar/navItems";
import type { Role } from "@/lib/api/types";
import { canDo, canOpenPath, canReach, canSearch, homeFor, idleMinutesFor } from "@/lib/roles";

const keysFor = (role: Role): string[] => navFor({ role, billing_only: false }).map((item) => item.key);
const BILLING_ONLY_ADMIN = { role: "admin", billing_only: true } as const;

describe("billing-only navigation", () => {
  it("offers a billing-only admin the settings entry with the plan tab and nothing else", () => {
    const [settings, ...others] = navFor(BILLING_ONLY_ADMIN);
    expect(others).toEqual([]);
    expect(settings).toMatchObject({ key: "settings", href: "/settings/plan" });
    expect(settings?.tabs?.map((tab) => tab.key)).toEqual(["plan"]);
    expect(homeFor(BILLING_ONLY_ADMIN)).toBe("/settings/plan");
    expect(canReach(BILLING_ONLY_ADMIN, "plan")).toBe(true);
    expect(canReach(BILLING_ONLY_ADMIN, "help")).toBe(false);
    expect(canReach(BILLING_ONLY_ADMIN, "account")).toBe(false);
    expect(canReach(BILLING_ONLY_ADMIN, "security")).toBe(false);
    expect(canSearch(BILLING_ONLY_ADMIN)).toBe(false);
  });

  it("opens only the plan path while billing-only, and every path once the plan is live", () => {
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/settings/plan")).toBe(true);
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/settings/setup")).toBe(false);
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/today")).toBe(false);
    expect(canOpenPath(BILLING_ONLY_ADMIN, "/notes/note-1")).toBe(false);
    expect(canOpenPath({ role: "admin", billing_only: false }, "/today")).toBe(true);
    expect(homeFor({ role: "admin", billing_only: false })).toBe("/today");
    expect(canSearch({ role: "admin", billing_only: false })).toBe(true);
  });
});

describe("role-based navigation", () => {
  it("shows each role only its own areas: admin 8, compliance 5, coder 4, CDI and billers 3", () => {
    expect(keysFor("admin")).toEqual(["today", "inbox", "upload", "queue", "compliance", "billing", "insights", "settings"]);
    expect(keysFor("coder")).toEqual(["today", "inbox", "upload", "queue"]);
    expect(keysFor("cdi")).toEqual(["today", "inbox", "queue"]);
    expect(keysFor("compliance")).toEqual(["today", "inbox", "queue", "compliance", "insights"]);
    expect(keysFor("biller")).toEqual(["today", "inbox", "billing"]);
    expect(keysFor("viewer")).toEqual(["today", "insights"]);
    expect(keysFor("hq")).toEqual(["hqOverview", "hqPractices", "hqOrganizations", "hqSpend", "hqUsage", "hqActivity", "hqDemos", "hqTeam", "hqSecurity"]);
  });

  it("keeps the review queue open to billers although their sidebar leaves it out", () => {
    expect(canReach({ role: "biller", billing_only: false }, "queue")).toBe(true);
    expect(canReach({ role: "biller", billing_only: false }, "account")).toBe(true);
  });

  it("gives each area only the tabs the role can open, and points the entry at the first", () => {
    const tabsOf = (role: Role, key: string) => navItemFor({ role, billing_only: false }, key)?.tabs?.map((tab) => tab.key);
    expect(tabsOf("admin", "settings")).toEqual(["setup", "team", "plan", "security"]);
    expect(tabsOf("admin", "insights")).toEqual(["overview", "quality", "accessLog", "usage"]);
    expect(tabsOf("compliance", "insights")).toEqual(["overview", "quality", "accessLog"]);
    expect(tabsOf("viewer", "insights")).toEqual(["overview"]);
    expect(tabsOf("biller", "billing")).toEqual(["readyToBill", "remittances"]);
    expect(navItemFor({ role: "admin", billing_only: false }, "settings")?.href).toBe("/settings/setup");
  });

  it("marks an area active on any of its tabs and picks the most specific tab", () => {
    const admin = { role: "admin", billing_only: false } as const;
    const settings = navItemFor(admin, "settings");
    const insights = navItemFor(admin, "insights");
    expect(settings && isActive(settings, "/settings/team")).toBe(true);
    expect(insights && isActive(insights, "/insights/access-log")).toBe(true);
    expect(insights && isActive(insights, "/settings/team")).toBe(false);
    expect(activeTab(insights?.tabs ?? [], "/insights/quality/review/sample-1")?.key).toBe("quality");
    expect(activeTab(insights?.tabs ?? [], "/insights")?.key).toBe("overview");
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
