import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { NoteHeader } from "@/lib/api/types";
import { StatusBanner } from "../components/StatusBanner";
import { reviewGroups } from "../reviewList";
import { finding, noteDetail } from "./fixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const RETURNED = { reason: "level_not_supported", note: "Exam repeated from the last visit", by: "Jordan Diaz", at: "2026-11-28T10:00:00Z", items: 1 } as const;

function header(overrides: Partial<NoteHeader>): NoteHeader {
  return { id: "note-1", status: "ready", lane: "coder", lane_reason: "returned", flag_reason: null, voided: null, returned: null, ...overrides } as NoteHeader;
}

function renderBanner(note: NoteHeader) {
  render(<StatusBanner note={note} reason={null} onRetry={null} onReopen={null} retryPending={false} canRestore={false} onRestored={vi.fn()} />);
}

describe("a note compliance returned", () => {
  it("says who returned it and why above the findings", () => {
    renderBanner(header({ returned: RETURNED }));
    expect(screen.getByText("Returned by Jordan Diaz: Level not supported · Exam repeated from the last visit")).toBeInTheDocument();
  });

  it("shows the reason alone when no note was written", () => {
    renderBanner(header({ returned: { ...RETURNED, note: null, by: null } }));
    expect(screen.getByText("Returned: Level not supported")).toBeInTheDocument();
  });

  it("puts the returned items first until each has a fresh decision", () => {
    const em = finding({ kind: "em", key: "em", action: "lower", code_before: "99215", code_after: "99213", choice: "accept", allowed: ["accept", "keep"] });
    const added = finding({ key: "dx:E11.65", action: "add", code_before: null, code_after: "E11.65", choice: "add", allowed: ["add", "skip"], amount_change: 0 });
    const groups = reviewGroups(noteDetail([added, { ...em, decide_again: true }]));
    expect(groups.blocking.map((row) => row.finding.key)).toEqual(["em"]);
    expect(groups.changes.map((row) => row.finding.key)).toEqual(["dx:E11.65"]);
  });
});
