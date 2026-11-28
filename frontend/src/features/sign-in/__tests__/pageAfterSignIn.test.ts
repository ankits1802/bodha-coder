import { describe, expect, it } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { sameSitePath } from "@/lib/paths";
import { pageAfterSignIn } from "../SignInScreen";

describe("pageAfterSignIn", () => {
  it("opens the new-practice page only when a practice account asked for it", () => {
    expect(pageAfterSignIn(CODER, "/practices/new")).toBe("/practices/new");
    expect(pageAfterSignIn(CODER, null)).toBe("/today");
    expect(pageAfterSignIn(CODER, "https://elsewhere.example.com")).toBe("/today");
    expect(pageAfterSignIn({ ...CODER, billing_only: true }, "/practices/new")).toBe("/settings/plan");
    expect(pageAfterSignIn({ ...CODER, role: "hq", practice: null, practices: [] }, "/practices/new")).toBe("/hq");
  });

  it("returns a practice account to the page it came from when that page is on this site", () => {
    expect(pageAfterSignIn(CODER, "/notes/n-1?history=1")).toBe("/notes/n-1?history=1");
    for (const elsewhere of ["//evil.example.com", "/\\evil.example.com", "/api/auth/refresh", "/sign-in", "notes", "/a b"]) {
      expect(pageAfterSignIn(CODER, elsewhere)).toBe("/today");
    }
  });
});

describe("sameSitePath", () => {
  it("keeps only paths that cannot leave the site", () => {
    expect(sameSitePath("/settings/security")).toBe("/settings/security");
    expect(sameSitePath("javascript:alert(1)")).toBeNull();
    expect(sameSitePath(`/${"a".repeat(600)}`)).toBeNull();
    expect(sameSitePath(undefined)).toBeNull();
  });
});
