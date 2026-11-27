import { describe, expect, it } from "vitest";
import { daysLeft, isEndingSoon, practiceToday } from "../practiceStatus";

const LAKESIDE = { status: "trial" as const, renews_on: "2026-12-11", time_zone: "America/Chicago" };
const EVENING_IN_CHICAGO = new Date("2026-11-27T20:32:00Z");

describe("days left on a plan", () => {
  it("counts from the practice's own calendar day, as the plan banner does, wherever HQ sits", () => {
    expect(practiceToday(LAKESIDE, EVENING_IN_CHICAGO)).toBe("2026-11-27");
    expect(daysLeft(LAKESIDE, practiceToday(LAKESIDE, EVENING_IN_CHICAGO))).toBe(14);
    const kolkata = { ...LAKESIDE, time_zone: "Asia/Kolkata" };
    expect(daysLeft(kolkata, practiceToday(kolkata, EVENING_IN_CHICAGO))).toBe(13);
  });

  it("has nothing to count without a renewal date, and calls fourteen days ending soon", () => {
    expect(daysLeft({ ...LAKESIDE, renews_on: null }, "2026-11-27")).toBeNull();
    expect(isEndingSoon(LAKESIDE, "2026-11-27")).toBe(true);
    expect(isEndingSoon(LAKESIDE, "2026-11-26")).toBe(false);
  });
});
