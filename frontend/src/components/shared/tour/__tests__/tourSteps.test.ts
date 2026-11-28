import { describe, expect, it } from "vitest";
import type { Role, TourRecord } from "@/lib/api/types";
import { NAV_ITEMS } from "../../sidebar/navItems";
import { TOUR_TEXT } from "../strings";
import { TOUR_VERSION, isTourDue, tourKeyFor, tourStepsFor } from "../tourSteps";

function keysFor(role: Role, billingOnly = false): string[] {
  return tourStepsFor({ role, billing_only: billingOnly }).map((step) => step.key);
}

function record(tour: TourRecord["tour"], version: number): TourRecord {
  return { tour, version, completed_at: "2026-11-28T10:00:00+00:00", skipped_at: null };
}

const MAX_WORDS = 12;

describe("tourStepsFor", () => {
  it("walks an admin through every sidebar area, the review steps and the access log under Insights", () => {
    expect(keysFor("admin")).toEqual([
      "welcome",
      "search",
      "today",
      "inbox",
      "upload",
      "queue",
      "decide",
      "evidence",
      "ask",
      "compliance",
      "billing",
      "insights",
      "accessLog",
      "settings",
      "help",
      "replay",
    ]);
  });

  it("shows a coder their work and the note review steps, and nothing an admin owns", () => {
    expect(keysFor("coder")).toEqual(["welcome", "search", "today", "inbox", "upload", "queue", "decide", "evidence", "ask", "help", "replay"]);
  });

  it("gives every other practice role exactly the areas its sidebar shows", () => {
    expect(keysFor("cdi")).toEqual(["welcome", "search", "today", "inbox", "queue", "decide", "evidence", "ask", "help", "replay"]);
    expect(keysFor("compliance")).toEqual([
      "welcome",
      "search",
      "today",
      "inbox",
      "queue",
      "decide",
      "evidence",
      "compliance",
      "insights",
      "accessLog",
      "help",
      "replay",
    ]);
    expect(keysFor("biller")).toEqual(["welcome", "search", "today", "inbox", "billing", "help", "replay"]);
    expect(keysFor("viewer")).toEqual(["welcome", "today", "insights", "help", "replay"]);
  });

  it("gives HQ a short tour of the console", () => {
    expect(keysFor("hq")).toEqual([
      "welcome",
      "hqOverview",
      "hqPractices",
      "hqOrganizations",
      "hqSpend",
      "hqUsage",
      "hqActivity",
      "hqDemos",
      "hqTeam",
      "hqSecurity",
      "replay",
    ]);
  });

  it("keeps a billing-only admin to the settings entry for the plan", () => {
    expect(keysFor("admin", true)).toEqual(["welcome", "settings", "replay"]);
    expect(tourStepsFor({ role: "admin", billing_only: true })[1]).toMatchObject({ target: "/settings/plan", path: "/settings/plan" });
  });

  it("points each area at its sidebar entry and opens its page", () => {
    const steps = tourStepsFor({ role: "admin", billing_only: false });
    const byKey = new Map(steps.map((step) => [step.key, step]));
    expect(byKey.get("queue")).toMatchObject({ title: "Review queue", target: "/queue", path: "/queue" });
    expect(byKey.get("settings")).toMatchObject({
      title: "Settings",
      line: "Providers, payers, checks, team, plan and security.",
      target: "/settings/setup",
      path: "/settings/setup",
    });
    expect(byKey.get("billing")).toMatchObject({ title: "Billing", target: "/billing", path: "/billing" });
    expect(byKey.get("decide")).toMatchObject({ title: "Accept or keep", target: null, path: "/queue" });
    expect(byKey.get("ask")).toMatchObject({ title: "Questions", target: null, path: "/queue" });
    expect(byKey.get("accessLog")).toMatchObject({ title: "Access log", target: "/insights", path: "/insights/access-log" });
    expect(byKey.get("search")).toMatchObject({ title: "Search", target: "search", path: null });
    expect(byKey.get("help")).toMatchObject({ title: "Help", target: "/help", path: "/help" });
    expect(byKey.get("welcome")).toMatchObject({ target: null, path: null });
    expect(byKey.get("replay")).toMatchObject({ title: "Your account", target: "tour", path: null });
  });

  it("has a line for every sidebar area, each short", () => {
    for (const item of NAV_ITEMS) expect(TOUR_TEXT.areas[item.key], item.key).toBeTruthy();
    const roles: Role[] = ["admin", "coder", "cdi", "compliance", "biller", "viewer", "hq"];
    for (const step of roles.flatMap((role) => tourStepsFor({ role, billing_only: false }))) {
      expect(step.line.split(" ").length, step.key).toBeLessThanOrEqual(MAX_WORDS);
    }
  });
});

describe("tour records", () => {
  it("names the tour by the account's console", () => {
    expect(tourKeyFor({ role: "hq", billing_only: false })).toBe("hq");
    expect(tourKeyFor({ role: "viewer", billing_only: false })).toBe("practice");
  });

  it("is due until this version of the same tour is recorded", () => {
    expect(isTourDue([], "practice")).toBe(true);
    expect(isTourDue([record("hq", TOUR_VERSION)], "practice")).toBe(true);
    expect(isTourDue([record("practice", TOUR_VERSION - 1)], "practice")).toBe(true);
    expect(isTourDue([record("practice", TOUR_VERSION)], "practice")).toBe(false);
  });
});
