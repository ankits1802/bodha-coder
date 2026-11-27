import { describe, expect, it } from "vitest";
import { canRenew, choosePreset, practiceToday, presetUntil, RENEWAL_PRESETS, renewalBase } from "../renewal";

describe("renewal presets", () => {
  it("counts from the later of today and the current end date, so renewing early loses no days", () => {
    expect(renewalBase({ renews_on: "2027-03-01" }, "2026-11-28")).toBe("2027-03-01");
    expect(renewalBase({ renews_on: "2026-10-01" }, "2026-11-28")).toBe("2026-11-28");
    expect(renewalBase({ renews_on: null }, "2026-11-28")).toBe("2026-11-28");
  });

  it("turns each preset into an end date, or none for no end date", () => {
    const ends = RENEWAL_PRESETS.map((preset) => presetUntil(preset, "2026-11-30"));
    expect(ends).toEqual(["2026-12-14", "2026-12-30", "2027-02-28", "2027-05-30", "2027-11-30", null]);
  });

  it("allows a date after today or no end date, never today or earlier", () => {
    expect(canRenew(choosePreset("noEnd", "2026-11-28"), "2026-11-28")).toBe(true);
    expect(canRenew({ preset: null, until: "2026-11-29" }, "2026-11-28")).toBe(true);
    expect(canRenew({ preset: null, until: "2026-11-28" }, "2026-11-28")).toBe(false);
    expect(canRenew({ preset: null, until: null }, "2026-11-28")).toBe(false);
  });

  it("reads today in the practice's own time zone", () => {
    const lateEvening = new Date("2026-11-29T03:30:00Z");
    expect(practiceToday({ time_zone: "America/Los_Angeles" }, lateEvening)).toBe("2026-11-28");
    expect(practiceToday({ time_zone: "Asia/Kolkata" }, lateEvening)).toBe("2026-11-29");
  });
});
