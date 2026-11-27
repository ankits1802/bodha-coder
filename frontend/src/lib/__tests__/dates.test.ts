import { describe, expect, it } from "vitest";
import { addMonths, clampIsoDate, isoDateInZone, isWithin, monthWeeks, weekdayOf } from "@/lib/dates";

describe("isoDateInZone", () => {
  const lateEveningInChicago = new Date(Date.UTC(2026, 10, 27, 3, 30));

  it("gives the calendar day in the practice time zone", () => {
    expect(isoDateInZone(lateEveningInChicago, "America/Chicago")).toBe("2026-11-26");
    expect(isoDateInZone(lateEveningInChicago, "Pacific/Honolulu")).toBe("2026-11-26");
    expect(isoDateInZone(lateEveningInChicago, "America/New_York")).toBe("2026-11-26");
    expect(isoDateInZone(lateEveningInChicago, "UTC")).toBe("2026-11-27");
  });

  it("pads month and day", () => {
    expect(isoDateInZone(new Date(Date.UTC(2026, 0, 5, 12, 0)), "America/Denver")).toBe("2026-01-05");
  });
});

describe("calendar arithmetic", () => {
  it("adds months and keeps the day where the month allows", () => {
    expect(addMonths("2026-01-31", 1)).toBe("2026-02-28");
    expect(addMonths("2024-01-31", 1)).toBe("2024-02-29");
    expect(addMonths("2026-11-27", -12)).toBe("2025-11-27");
    expect(addMonths("2026-12-15", 1)).toBe("2027-01-15");
    expect(addMonths("not a date", 1)).toBeNull();
  });

  it("clamps a day into an optional range", () => {
    expect(clampIsoDate("2026-12-01", null, "2026-11-27")).toBe("2026-11-27");
    expect(clampIsoDate("2026-01-01", "2026-03-15")).toBe("2026-03-15");
    expect(clampIsoDate("2026-06-01", "2026-03-15", "2026-11-27")).toBe("2026-06-01");
    expect(isWithin("2026-11-28", undefined, "2026-11-27")).toBe(false);
    expect(isWithin("2026-11-27", "2026-11-27", "2026-11-27")).toBe(true);
  });

  it("names the weekday of a day", () => {
    expect(weekdayOf("2026-11-27")).toBe(5);
    expect(weekdayOf("2026-11-29")).toBe(0);
  });

  it("lays a month out in weeks that start on Monday", () => {
    const weeks = monthWeeks(2026, 11, 1);
    expect(weeks).toHaveLength(6);
    expect(weeks[0]).toEqual([null, null, null, null, null, null, "2026-11-01"]);
    expect(weeks[1]?.[0]).toBe("2026-11-02");
    expect(weeks[4]?.[4]).toBe("2026-11-27");
    expect(weeks[5]).toEqual(["2026-11-30", null, null, null, null, null, null]);
  });
});
