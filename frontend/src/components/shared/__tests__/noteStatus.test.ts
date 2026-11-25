import { describe, expect, it } from "vitest";
import { noteStatus } from "@/components/shared/noteStatus";
import type { EmAction, NoteSummary } from "@/lib/api/types";

type Fields = Pick<NoteSummary, "status" | "lane" | "lane_reason" | "headline"> & { em_action?: EmAction | null };

function ready(fields: Partial<Fields>): Fields {
  return { status: "ready", lane: "coder", lane_reason: null, headline: null, ...fields };
}

describe("noteStatus", () => {
  it("takes the tone from the lane reason and the word from the headline", () => {
    expect(noteStatus(ready({ lane: "compliance", lane_reason: "levels_too_high", headline: "2 levels too high" }))).toEqual({
      tone: "bad",
      label: "2 levels too high",
    });
    expect(noteStatus(ready({ lane: "compliance", lane_reason: "flagged", headline: "Flagged for compliance" })).tone).toBe("warn");
    expect(noteStatus(ready({ lane: "provider", lane_reason: "waiting_on_provider", headline: "Waiting on provider" })).tone).toBe("warn");
    expect(noteStatus(ready({ lane: "approve", lane_reason: "matches", headline: "Matches the note" })).tone).toBe("ok");
  });

  it("tells billed too high from billed too low by the visit code suggestion, not the wording", () => {
    expect(noteStatus(ready({ lane_reason: "code_changes", em_action: "lower", headline: "Any wording" })).tone).toBe("bad");
    expect(noteStatus(ready({ lane_reason: "code_changes", em_action: "raise", headline: "Any wording" })).tone).toBe("low");
    expect(noteStatus(ready({ lane_reason: "code_changes", em_action: "replace", headline: null })).tone).toBe("bad");
    expect(noteStatus(ready({ lane_reason: "code_changes", em_action: "keep", headline: "Diagnosis missing" })).tone).toBe("dark");
    expect(noteStatus(ready({ lane_reason: "code_changes", headline: "Billed too high" })).tone).toBe("dark");
  });

  it("describes notes that are not open for review by their status", () => {
    expect(noteStatus({ status: "reading", lane: null, lane_reason: null, headline: null })).toEqual({ tone: "neutral", label: "Reading…" });
    expect(noteStatus({ status: "failed", lane: null, lane_reason: null, headline: null })).toEqual({ tone: "bad", label: "Could not read" });
  });
});
