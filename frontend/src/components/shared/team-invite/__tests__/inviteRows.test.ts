import { describe, expect, it } from "vitest";
import { blankRow, blankRows, filledRows, nextRowId, readyToSend, rowErrors, type InviteRow } from "../inviteRows";

function row(id: number, name: string, email: string): InviteRow {
  return { ...blankRow(id), name, email };
}

describe("invite rows", () => {
  it("starts with three empty rows for coders and numbers new rows after the highest", () => {
    const rows = blankRows(3);
    expect(rows.map((item) => [item.id, item.role, item.name])).toEqual([
      [0, "coder", ""],
      [1, "coder", ""],
      [2, "coder", ""],
    ]);
    expect(nextRowId([row(0, "", ""), row(4, "", "")])).toBe(5);
  });

  it("leaves untouched rows out and asks for a name and a valid email on the others", () => {
    const rows = [row(0, "Lee Park", "lee@lakeside.example.com"), row(1, "", ""), row(2, "Ana Ruiz", "ana@")];
    expect(filledRows(rows).map((item) => item.id)).toEqual([0, 2]);
    expect(rowErrors(rows[1] as InviteRow)).toEqual({});
    expect(rowErrors(rows[2] as InviteRow)).toEqual({ email: "Enter a valid email" });
    expect(rowErrors(row(3, "", "sam@lakeside.example.com"))).toEqual({ name: "Enter a name" });
    expect(readyToSend(rows)).toBe(false);
    expect(readyToSend(rows.slice(0, 2))).toBe(true);
    expect(readyToSend(blankRows(3))).toBe(false);
  });
});
