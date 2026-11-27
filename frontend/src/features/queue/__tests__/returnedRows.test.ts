import { describe, expect, it } from "vitest";
import { noteStatus } from "@/components/shared/noteStatus";
import { bulkAbilities, isApprovable, noteHref } from "../queueRules";
import { CODER, ROW } from "./fixtures";

const RETURNED = { ...ROW, lane: "coder", lane_reason: "returned", headline: "Returned" } as const;
const MATCHES = { ...ROW, id: "note-2", lane: "approve", lane_reason: "matches", headline: "Matches the note" } as const;

describe("returned notes in the queue", () => {
  it("are marked Returned in the coder's lane, never as matching the note", () => {
    expect(noteStatus(RETURNED)).toEqual({ tone: "warn", label: "Returned" });
  });

  it("can never be approved together with other notes", () => {
    expect(isApprovable(MATCHES)).toBe(true);
    expect(isApprovable(RETURNED)).toBe(false);
    expect(isApprovable({ ...RETURNED, lane: "approve" })).toBe(false);
    expect(bulkAbilities([MATCHES, RETURNED], CODER).approve).toBe(false);
  });

  it("open with the lane and its split so next and previous stay inside it", () => {
    expect(noteHref("note-1", "provider", "questions")).toBe("/notes/note-1?lane=provider&reason=questions");
    expect(noteHref("note-1", "coder")).toBe("/notes/note-1?lane=coder");
    expect(noteHref("note-1", undefined)).toBe("/notes/note-1");
  });
});
