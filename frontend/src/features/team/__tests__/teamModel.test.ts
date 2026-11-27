import { describe, expect, it } from "vitest";
import { accessLogPath } from "@/lib/paths";
import { activityRange } from "../teamModel";

describe("a person's activity", () => {
  it("covers the last thirty days of the practice calendar, today included", () => {
    expect(activityRange("2026-11-28")).toEqual({ start: "2026-10-30", end: "2026-11-28" });
    expect(activityRange("2026-03-01")).toEqual({ start: "2026-01-31", end: "2026-03-01" });
  });

  it("opens the access log filtered to that person and range", () => {
    expect(accessLogPath("user-sam", { start: "2026-10-30", end: "2026-11-28" })).toBe(
      "/insights/access-log?user=user-sam&start=2026-10-30&end=2026-11-28",
    );
  });
});
