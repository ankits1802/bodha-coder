import { describe, expect, it } from "vitest";
import { accessLogFilters, filterChanges } from "../accessLog";

function reader(params: Record<string, string>): (name: string) => string | null {
  return (name) => params[name] ?? null;
}

describe("access log filters", () => {
  it("reads every filter from the address and defaults the days to today", () => {
    const filters = accessLogFilters(
      reader({ start: "2026-11-01", end: "2026-11-27", user: "u1", action: "opened note", note: " n1 ", patient: "Reyes", born: "1959-03-02" }),
      "2026-11-28",
    );
    expect(filters).toEqual({
      start: "2026-11-01",
      end: "2026-11-27",
      user_id: "u1",
      action: "opened note",
      note_id: "n1",
      patient: "Reyes",
      birth_date: "1959-03-02",
    });
    expect(accessLogFilters(reader({}), "2026-11-28")).toEqual({
      start: "2026-11-28",
      end: "2026-11-28",
      user_id: null,
      action: null,
      note_id: null,
      patient: null,
      birth_date: null,
    });
  });

  it("never sends an end before the start or a day it cannot read", () => {
    const filters = accessLogFilters(reader({ start: "2026-11-20", end: "2026-11-02", born: "02/03/1959" }), "2026-11-28");
    expect([filters.start, filters.end, filters.birth_date]).toEqual(["2026-11-20", "2026-11-20", null]);
  });

  it("writes changes back to the address and starts again from the first page", () => {
    expect(filterChanges({ patient: "  Reyes ", note_id: "", birth_date: null })).toEqual({
      patient: "Reyes",
      note: null,
      born: null,
      offset: null,
    });
  });
});
