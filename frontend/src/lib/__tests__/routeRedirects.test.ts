import { describe, expect, it } from "vitest";
import robots from "@/app/robots";
import { ROUTE_REDIRECTS } from "../routeRedirects";
import { PLAN_PATH } from "../roles";

function destinationOf(source: string): string | undefined {
  return ROUTE_REDIRECTS.find((route) => route.source === source)?.destination;
}

describe("moved pages", () => {
  it("sends every old address to its tab, keeping the blind audit's id", () => {
    expect(destinationOf("/setup")).toBe("/settings/setup");
    expect(destinationOf("/team")).toBe("/settings/team");
    expect(destinationOf("/plan")).toBe("/settings/plan");
    expect(destinationOf("/remittances")).toBe("/billing/remittances");
    expect(destinationOf("/quality")).toBe("/insights/quality");
    expect(destinationOf("/quality/review/:sampleId")).toBe("/insights/quality/review/:sampleId");
    expect(destinationOf("/settings")).toBe("/settings/setup");
  });

  it("points the old plan address where checkout and the banner now return", () => {
    expect(destinationOf("/plan")).toBe(PLAN_PATH);
  });

  it("keeps the new private areas out of search engines", () => {
    const rule = robots().rules;
    const disallow = (Array.isArray(rule) ? rule[0] : rule)?.disallow;
    expect(disallow).toEqual(expect.arrayContaining(["/settings", "/account", "/practices/", "/plan", "/setup", "/quality"]));
  });
});
