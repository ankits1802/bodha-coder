import { describe, expect, it } from "vitest";
import { cardPrice, limitLines, mostMonthsFree } from "../planPrice";
import { ENTERPRISE_TERMS, ESSENTIALS_TERMS, PROFESSIONAL_TERMS, TRIAL_TERMS } from "./planFixtures";

describe("plan card prices", () => {
  it("shows the price per provider for the chosen period in whole dollars", () => {
    expect(cardPrice(ESSENTIALS_TERMS, "monthly", 14)).toEqual({ amount: "$149", unit: "per provider / month" });
    expect(cardPrice(ESSENTIALS_TERMS, "annual", 14)).toEqual({ amount: "$1,490", unit: "per provider / year" });
    expect(cardPrice(PROFESSIONAL_TERMS, "annual", 14)).toEqual({ amount: "$2,490", unit: "per provider / year" });
  });

  it("shows the trial as free for its length and enterprise as custom", () => {
    expect(cardPrice(TRIAL_TERMS, "annual", 14)).toEqual({ amount: "Free", unit: "for 14 days" });
    expect(cardPrice(ENTERPRISE_TERMS, "monthly", 14)).toEqual({ amount: "Custom", unit: "for larger groups" });
  });

  it("lists the limits, unlimited where the plan has none", () => {
    expect(limitLines(ESSENTIALS_TERMS)).toEqual(["Up to 5 users", "Up to 3 providers", "Every feature included"]);
    expect(limitLines(PROFESSIONAL_TERMS)).toEqual(["Unlimited users", "Up to 50 providers", "Every feature included"]);
  });

  it("names the months a yearly plan saves, or nothing when no plan saves any", () => {
    expect(mostMonthsFree([TRIAL_TERMS, ESSENTIALS_TERMS, PROFESSIONAL_TERMS, ENTERPRISE_TERMS])).toBe(2);
    expect(mostMonthsFree([TRIAL_TERMS, ENTERPRISE_TERMS])).toBeNull();
  });
});
