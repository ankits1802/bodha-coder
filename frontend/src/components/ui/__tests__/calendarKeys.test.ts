import { describe, expect, it } from "vitest";
import { canShowEarlier, canShowLater, monthOptions, yearOptions } from "../date/calendarModel";
import { dayForKey } from "../date/calendarKeys";

const MONDAY = 1;

describe("calendar keys", () => {
  it("moves by day and by week, across month ends", () => {
    expect(dayForKey("2026-11-27", "ArrowRight", false, MONDAY)).toBe("2026-11-28");
    expect(dayForKey("2026-11-30", "ArrowRight", false, MONDAY)).toBe("2026-12-01");
    expect(dayForKey("2026-11-01", "ArrowLeft", false, MONDAY)).toBe("2026-10-31");
    expect(dayForKey("2026-11-27", "ArrowDown", false, MONDAY)).toBe("2026-12-04");
    expect(dayForKey("2026-11-27", "ArrowUp", false, MONDAY)).toBe("2026-11-20");
  });

  it("moves by month, and by year with Shift, keeping the day where the month allows", () => {
    expect(dayForKey("2026-11-27", "PageDown", false, MONDAY)).toBe("2026-12-27");
    expect(dayForKey("2026-01-31", "PageDown", false, MONDAY)).toBe("2026-02-28");
    expect(dayForKey("2026-11-27", "PageUp", true, MONDAY)).toBe("2025-11-27");
    expect(dayForKey("2024-02-29", "PageDown", true, MONDAY)).toBe("2025-02-28");
  });

  it("goes to the start and end of a week that starts on Monday", () => {
    expect(dayForKey("2026-11-27", "Home", false, MONDAY)).toBe("2026-11-23");
    expect(dayForKey("2026-11-27", "End", false, MONDAY)).toBe("2026-11-29");
    expect(dayForKey("2026-11-29", "Home", false, MONDAY)).toBe("2026-11-23");
  });

  it("ignores other keys", () => {
    expect(dayForKey("2026-11-27", "Enter", false, MONDAY)).toBeNull();
  });
});

describe("calendar header choices", () => {
  it("allows earlier and later months only while they hold a day in range", () => {
    expect(canShowEarlier(2026, 11, "2026-11-01")).toBe(false);
    expect(canShowEarlier(2026, 11, "2026-10-31")).toBe(true);
    expect(canShowLater(2026, 11, "2026-11-30")).toBe(false);
    expect(canShowLater(2026, 11, "2026-12-01")).toBe(true);
    expect(canShowLater(2026, 11)).toBe(true);
  });

  it("disables months that lie wholly outside the range", () => {
    const months = monthOptions(2026, "2026-03-15", "2026-11-27");
    expect(months.filter((month) => !month.disabled).map((month) => month.label)).toEqual([
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
    ]);
  });

  it("lists the years between the limits", () => {
    expect(yearOptions(2025, "2026-11-27", "2023-05-01", "2026-11-27").map((year) => year.value)).toEqual(["2023", "2024", "2025", "2026"]);
    const open = yearOptions(2026, "2026-11-27");
    expect(open[0]?.value).toBe("1926");
    expect(open[open.length - 1]?.value).toBe("2036");
  });
});
