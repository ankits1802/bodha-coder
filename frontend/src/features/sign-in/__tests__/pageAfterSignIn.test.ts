import { describe, expect, it } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { pageAfterSignIn } from "../SignInScreen";

describe("pageAfterSignIn", () => {
  it("opens the new-practice page only when a practice account asked for it", () => {
    expect(pageAfterSignIn(CODER, "/practices/new")).toBe("/practices/new");
    expect(pageAfterSignIn(CODER, null)).toBe("/today");
    expect(pageAfterSignIn(CODER, "https://elsewhere.example.com")).toBe("/today");
    expect(pageAfterSignIn({ ...CODER, billing_only: true }, "/practices/new")).toBe("/plan");
    expect(pageAfterSignIn({ ...CODER, role: "hq", practice: null, practices: [] }, "/practices/new")).toBe("/hq");
  });
});
