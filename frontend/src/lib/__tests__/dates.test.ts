import { describe, expect, it } from "vitest";
import { isoDateInZone } from "@/lib/dates";

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
