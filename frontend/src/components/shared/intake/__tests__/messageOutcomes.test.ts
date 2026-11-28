import { describe, expect, it } from "vitest";
import type { IntakeMessage } from "@/lib/api/types";
import { messageSummary, messageTone, refusedReasons } from "../messageOutcomes";

const ACCEPTED: IntakeMessage = {
  id: "m1",
  received_at: "2026-11-28T10:00:00Z",
  sender: "scans@lakeside.example.com",
  outcome: "accepted",
  reason: null,
  accepted_files: 2,
  refused_files: 0,
  files: [
    { outcome: "accepted", reason: null, note_id: "n1" },
    { outcome: "accepted", reason: null, note_id: "n2" },
  ],
};

describe("intake messages", () => {
  it("says how many files were accepted and how many refused", () => {
    expect(messageSummary(ACCEPTED)).toBe("Accepted 2 files");
    const mixed: IntakeMessage = { ...ACCEPTED, accepted_files: 1, refused_files: 2 };
    expect(messageSummary(mixed)).toBe("Accepted 1 file, 2 files refused");
    expect(messageTone(mixed)).toBe("warn");
    expect(messageTone(ACCEPTED)).toBe("ok");
  });

  it("names why a message was refused", () => {
    const refused: IntakeMessage = { ...ACCEPTED, outcome: "refused", reason: "not_authenticated", accepted_files: 0, files: [] };
    expect(messageSummary(refused)).toBe("Sender not verified");
    expect(messageTone(refused)).toBe("bad");
    expect(messageSummary({ ...refused, outcome: "test", reason: null })).toBe("Test");
  });

  it("lists each reason a file was refused once, as a sentence", () => {
    const files: IntakeMessage["files"] = [
      { outcome: "refused", reason: "only PDF files are read", note_id: null },
      { outcome: "refused", reason: "only PDF files are read", note_id: null },
      { outcome: "accepted", reason: null, note_id: "n1" },
    ];
    expect(refusedReasons({ ...ACCEPTED, files })).toEqual(["Only PDF files are read"]);
  });
});
