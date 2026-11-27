import { describe, expect, it } from "vitest";
import { securityDestination } from "../securityDestination";

describe("the old security address", () => {
  it("sends admins to the practice security settings and keeps an access log filter for the log", () => {
    expect(securityDestination({ role: "admin", billing_only: false }, "")).toBe("/settings/security");
    expect(securityDestination({ role: "admin", billing_only: false }, "user=user-9&start=2026-11-01")).toBe(
      "/insights/access-log?user=user-9&start=2026-11-01",
    );
  });

  it("sends compliance to the access log and everyone else to their account", () => {
    expect(securityDestination({ role: "compliance", billing_only: false }, "")).toBe("/insights/access-log");
    expect(securityDestination({ role: "coder", billing_only: false }, "user=user-9")).toBe("/account");
    expect(securityDestination({ role: "biller", billing_only: false }, "")).toBe("/account");
  });
});
