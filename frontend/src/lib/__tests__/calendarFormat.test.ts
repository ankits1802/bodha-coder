import { describe, expect, it } from "vitest";
import { MONTH_NAMES, WEEKDAY_NAMES, formatCalendarDay, formatMonthYear, parseCalendarDay } from "@/lib/format";

describe("parseCalendarDay", () => {
  it("reads the app's own day format, with or without a weekday", () => {
    expect(parseCalendarDay("27 Nov 2026")).toBe("2026-11-27");
    expect(parseCalendarDay("Fri 27 Nov 2026")).toBe("2026-11-27");
    expect(parseCalendarDay(" 27 November 2026 ")).toBe("2026-11-27");
    expect(parseCalendarDay("3 Sept 2026")).toBe("2026-09-03");
    expect(parseCalendarDay("3 sep 2026")).toBe("2026-09-03");
  });

  it("reads day-first numbers and ISO dates", () => {
    expect(parseCalendarDay("27/11/2026")).toBe("2026-11-27");
    expect(parseCalendarDay("3.2.2026")).toBe("2026-02-03");
    expect(parseCalendarDay("3-2-2026")).toBe("2026-02-03");
    expect(parseCalendarDay("2026-11-27")).toBe("2026-11-27");
  });

  it("refuses days that do not exist and text it cannot read", () => {
    expect(parseCalendarDay("31 Feb 2026")).toBeNull();
    expect(parseCalendarDay("29/02/2026")).toBeNull();
    expect(parseCalendarDay("13/13/2026")).toBeNull();
    expect(parseCalendarDay("27 Nov 26")).toBeNull();
    expect(parseCalendarDay("Nov 27 2026")).toBeNull();
    expect(parseCalendarDay("27 Nv 2026")).toBeNull();
    expect(parseCalendarDay("")).toBeNull();
  });

  it("reads back what formatCalendarDay writes", () => {
    expect(parseCalendarDay(formatCalendarDay("2026-09-03", "year"))).toBe("2026-09-03");
    expect(parseCalendarDay(formatCalendarDay("2024-02-29", "long"))).toBe("2024-02-29");
  });
});

describe("calendar names", () => {
  it("spells a whole day for screen readers", () => {
    expect(formatCalendarDay("2026-11-27", "complete")).toBe("Friday 27 November 2026");
  });

  it("names the month and year, the months and the weekdays from Monday", () => {
    expect(formatMonthYear(2026, 11)).toBe("November 2026");
    expect(MONTH_NAMES).toHaveLength(12);
    expect(MONTH_NAMES[0]).toBe("January");
    expect(MONTH_NAMES[11]).toBe("December");
    expect(WEEKDAY_NAMES.map((name) => name.long)).toEqual(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]);
    expect(WEEKDAY_NAMES[0]?.narrow).toBe("M");
  });
});
