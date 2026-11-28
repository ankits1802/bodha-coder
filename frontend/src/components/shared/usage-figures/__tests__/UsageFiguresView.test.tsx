import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { UsageFigures } from "@/lib/api/types";
import { UsageFiguresView, hasUsage } from "../UsageFiguresView";

const FIGURES: UsageFigures = {
  days: 14,
  tasks: [
    {
      task: "note_review",
      role: "coder",
      tasks: 3,
      completed: 2,
      people: 1,
      duration: { p25: 15, median: 20, p75: 90 },
      first_decision: { p25: 3, median: 4, p75: 5 },
      decided: 6,
      inputs_per_decision: { p25: 2.5, median: 3, p75: 4 },
      keyboard_share: 0.5,
    },
    {
      task: "upload",
      role: "admin",
      tasks: 1,
      completed: 1,
      people: 1,
      duration: { p25: 30, median: 30, p75: 30 },
      first_decision: null,
      decided: 0,
      inputs_per_decision: null,
      keyboard_share: null,
    },
  ],
  stalls: [{ task: "note_review", step: "findings", role: "coder", stalls: 2, people: 1, duration: { p25: 67.5, median: 75, p75: 82.5 } }],
};

describe("UsageFiguresView", () => {
  it("shows medians with their spread by task and role, and no person", () => {
    render(<UsageFiguresView figures={FIGURES} />);

    const tasks = screen.getByRole("table", { name: "Time per task by role" });
    const review = within(tasks).getByRole("row", { name: /Note review/ });
    expect(within(review).getByText("Coder")).toBeInTheDocument();
    expect(within(review).getByText("2 of 3")).toBeInTheDocument();
    expect(within(review).getByText("20 s")).toBeInTheDocument();
    expect(within(review).getByText("15 s – 1.5 min")).toBeInTheDocument();
    expect(within(review).getByText("50%")).toBeInTheDocument();
    const upload = within(tasks).getByRole("row", { name: /Upload/ });
    expect(within(upload).getAllByText("—")).toHaveLength(3);
  });

  it("shows where people stall", () => {
    render(<UsageFiguresView figures={FIGURES} />);

    const stalls = screen.getByRole("table", { name: "Stalls by step and role" });
    const row = within(stalls).getByRole("row", { name: /Findings/ });
    expect(within(row).getByText("1.3 min")).toBeInTheDocument();
    expect(within(row).getByText("1.1 min – 1.4 min")).toBeInTheDocument();
  });

  it("says when nothing was recorded", () => {
    const empty = { ...FIGURES, tasks: [], stalls: [] };
    render(<UsageFiguresView figures={empty} />);

    expect(hasUsage(empty)).toBe(false);
    expect(screen.getByText("No timed tasks in this period")).toBeInTheDocument();
    expect(screen.getByText("No stalls in this period")).toBeInTheDocument();
  });
});
