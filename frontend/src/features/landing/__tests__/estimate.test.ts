import { describe, expect, it } from "vitest";
import { estimateWorth, levelDollars, readAmount, readDrafts, WORTH_BOUNDS, WORTH_DEFAULTS } from "../worth/estimate";

describe("worth estimate", () => {
  it("starts from 1,000 visits, 5% low, 3% high and $40 a level", () => {
    expect(WORTH_DEFAULTS).toEqual({ visits: 1000, lowPercent: 5, highPercent: 3, difference: 40 });
  });

  it("multiplies visits by the share billed one level off and the payment difference", () => {
    expect(levelDollars(1000, 5, 40)).toBe(2000);
    expect(levelDollars(1000, 3, 40)).toBe(1200);
    expect(levelDollars(0, 5, 40)).toBe(0);
    expect(levelDollars(1000, 0, 40)).toBe(0);
  });

  it("reports both directions for a month and a year", () => {
    expect(estimateWorth(WORTH_DEFAULTS)).toEqual({ recovered: 2000, exposure: 1200, recoveredYear: 24000, exposureYear: 14400 });
    const worth = estimateWorth({ visits: 2400, lowPercent: 7.5, highPercent: 2, difference: 55.5 });
    expect(worth.recovered).toBeCloseTo(9990, 6);
    expect(worth.exposure).toBeCloseTo(2664, 6);
    expect(worth.recoveredYear).toBeCloseTo(119880, 6);
    expect(worth.exposureYear).toBeCloseTo(31968, 6);
  });

  it("reads a typed amount only when it is a number inside its bounds", () => {
    const percent = WORTH_BOUNDS.lowPercent;
    expect(readAmount(" 12.5 ", percent)).toBe(12.5);
    expect(readAmount("0", percent)).toBe(0);
    expect(readAmount("30", percent)).toBe(30);
    expect(readAmount("30.5", percent)).toBeNull();
    expect(readAmount("-1", percent)).toBeNull();
    expect(readAmount("", percent)).toBeNull();
    expect(readAmount("five", percent)).toBeNull();
    expect(readAmount("10001", WORTH_BOUNDS.visits)).toBeNull();
  });

  it("refuses the whole estimate while any field is invalid", () => {
    expect(readDrafts({ visits: "1200", lowPercent: "4", highPercent: "2.5", difference: "35" })).toEqual({
      visits: 1200,
      lowPercent: 4,
      highPercent: 2.5,
      difference: 35,
    });
    expect(readDrafts({ visits: "1200", lowPercent: "", highPercent: "2.5", difference: "35" })).toBeNull();
    expect(readDrafts({ visits: "1200", lowPercent: "4", highPercent: "2.5", difference: "301" })).toBeNull();
  });
});
