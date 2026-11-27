import { describe, expect, it } from "vitest";
import { presetOf, presetRange, rangeFrom, spendCsv, spendFileName, utcToday } from "../spendModel";
import { NOVEMBER_SPEND } from "./spendFixtures";

const NOV_28 = { year: 2026, month: 11, day: 28 };

describe("spend range presets", () => {
  it("reads each preset from the UTC day", () => {
    expect(presetRange("thisMonth", NOV_28)).toEqual({ from: "2026-11-01", to: "2026-11-28" });
    expect(presetRange("lastMonth", NOV_28)).toEqual({ from: "2026-10-01", to: "2026-10-31" });
    expect(presetRange("last30Days", NOV_28)).toEqual({ from: "2026-10-30", to: "2026-11-28" });
    expect(presetRange("thisYear", NOV_28)).toEqual({ from: "2026-01-01", to: "2026-11-28" });
  });

  it("crosses into the previous year and knows a leap February", () => {
    const january = { year: 2027, month: 1, day: 5 };
    expect(presetRange("lastMonth", january)).toEqual({ from: "2026-12-01", to: "2026-12-31" });
    expect(presetRange("last30Days", january)).toEqual({ from: "2026-12-07", to: "2027-01-05" });
    expect(presetRange("lastMonth", { year: 2028, month: 3, day: 10 })).toEqual({ from: "2028-02-01", to: "2028-02-29" });
  });

  it("takes today from UTC, not the browser's zone", () => {
    expect(utcToday(new Date("2026-11-30T23:30:00-05:00"))).toEqual({ year: 2026, month: 12, day: 1 });
  });

  it("names the preset a range matches and none for a custom range", () => {
    expect(presetOf({ from: "2026-10-01", to: "2026-10-31" }, NOV_28)).toBe("lastMonth");
    expect(presetOf({ from: "2026-11-03", to: "2026-11-20" }, NOV_28)).toBeNull();
  });

  it("keeps a whole range from the address and falls back to this month otherwise", () => {
    expect(rangeFrom("2026-11-03", "2026-11-20", NOV_28)).toEqual({ from: "2026-11-03", to: "2026-11-20" });
    const thisMonth = { from: "2026-11-01", to: "2026-11-28" };
    expect(rangeFrom("2026-11-20", "2026-11-03", NOV_28)).toEqual(thisMonth);
    expect(rangeFrom("2026-02-30", "2026-03-03", NOV_28)).toEqual(thisMonth);
    expect(rangeFrom(null, "2026-11-20", NOV_28)).toEqual(thisMonth);
  });
});

describe("spend CSV", () => {
  it("has one row per provider with cost to the cent and cost per note finer", () => {
    expect(spendCsv(NOVEMBER_SPEND).split("\n")).toEqual([
      "practice,provider,analyses,notes_reviewed,input_tokens,output_tokens,cost_usd,cost_per_note_usd,analyses_without_price",
      "Lakeside,Elena Varga,3,1,1220000,150000,1.06,1.0600,0",
      "Lakeside,Omar Haddad,2,2,130000,16000,0.08,,1",
      '"Hillside, PC",Ana Ruiz,1,1,2000000,0,1.00,1.0000,0',
    ]);
  });

  it("names the file after the range", () => {
    expect(spendFileName({ from: "2026-11-01", to: "2026-11-28" })).toBe("bodha-spend-20261101-20261128.csv");
  });
});
