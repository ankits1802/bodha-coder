import { describe, expect, it } from "vitest";
import { canOpenPath, homeFor, isOrganizationAdmin, type SessionUser } from "@/lib/roles";

const ORGANIZATIONS = [{ id: "org-1", name: "Acme Health", role: "admin" as const }];
const BILLING_ONLY_COORDINATOR: SessionUser = { role: "coder", billing_only: true, organizations: ORGANIZATIONS };

describe("organization access", () => {
  it("lets a billing-only organization admin open only the plans they can pay", () => {
    expect(canOpenPath(BILLING_ONLY_COORDINATOR, "/organizations/org-1/plan")).toBe(true);
    expect(canOpenPath(BILLING_ONLY_COORDINATOR, "/settings/plan")).toBe(true);
    expect(canOpenPath(BILLING_ONLY_COORDINATOR, "/organizations/org-1")).toBe(false);
    expect(canOpenPath(BILLING_ONLY_COORDINATOR, "/organizations/org-2/plan")).toBe(false);
    expect(homeFor(BILLING_ONLY_COORDINATOR)).toBe("/organizations/org-1/plan");
    expect(homeFor({ ...BILLING_ONLY_COORDINATOR, role: "admin" })).toBe("/settings/plan");
    expect(homeFor({ role: "coder", billing_only: true })).toBe("/settings/plan");
  });

  it("knows which organizations a person runs", () => {
    expect(isOrganizationAdmin(BILLING_ONLY_COORDINATOR, "org-1")).toBe(true);
    expect(isOrganizationAdmin(BILLING_ONLY_COORDINATOR, "org-2")).toBe(false);
    expect(isOrganizationAdmin({ role: "admin", billing_only: false }, "org-1")).toBe(false);
    expect(isOrganizationAdmin(null, "org-1")).toBe(false);
  });
});
