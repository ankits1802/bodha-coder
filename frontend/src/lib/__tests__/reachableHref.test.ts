import { describe, expect, it } from "vitest";
import type { Role } from "@/lib/api/types";
import { reachableHref, type SessionUser } from "../roles";

function person(role: Role, billingOnly = false): SessionUser {
  return { role, billing_only: billingOnly, organizations: [] };
}

describe("an address a figure may open", () => {
  it("is kept only for a role that opens the area", () => {
    expect(reachableHref(person("biller"), "billing", "/billing?show=today")).toBe("/billing?show=today");
    expect(reachableHref(person("coder"), "billing", "/billing?show=today")).toBeNull();
    expect(reachableHref(person("viewer"), "queue", "/queue?lane=coder")).toBeNull();
  });

  it("is dropped in a billing-only session and without a session", () => {
    expect(reachableHref(person("admin", true), "billing", "/billing")).toBeNull();
    expect(reachableHref(null, "hq", "/hq/organizations")).toBeNull();
  });
});
