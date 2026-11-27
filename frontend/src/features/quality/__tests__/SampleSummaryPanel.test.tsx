import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AgreementSummary, WilsonRate } from "@/lib/api/types";
import { SampleSummaryPanel } from "../components/SampleSummaryPanel";

function rate(successes: number, trials: number, low: number, high: number): WilsonRate {
  return { successes, trials, value: successes / trials, low, high };
}

const HALF = rate(1, 2, 0.094531, 0.905469);

const SUMMARY: AgreementSummary = {
  notes: 2,
  em: HALF,
  em_higher: rate(0, 2, 0, 0.65762),
  em_lower: HALF,
  em_other: 0,
  icd_precision: rate(7, 8, 0.529112, 0.977583),
  icd_recall: rate(7, 8, 0.529112, 0.977583),
  icd_f1: 0.875,
  icd_exact: rate(0, 2, 0, 0.65762),
  modifiers: HALF,
};

describe("SampleSummaryPanel", () => {
  it("lists every element with its 95% Wilson interval in the table view", () => {
    render(<SampleSummaryPanel summary={SUMMARY} side="bodha" display="table" />);

    const table = screen.getByRole("table", { name: "Agreement of Bodha with the auditor, 95% Wilson intervals" });
    const rows = within(table).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("E/M exact50%9.5%90.5%1 of 2");
    expect(rows[2]).toHaveTextContent("ICD-10 precision87.5%52.9%97.8%7 of 8");
    expect(rows[4]).toHaveTextContent("ICD-10 exact set0%0%65.8%0 of 2");
    expect(rows[5]).toHaveTextContent("Modifiers50%9.5%90.5%1 of 2");
  });

  it("writes the value and interval beside each mark in the chart view", () => {
    render(<SampleSummaryPanel summary={SUMMARY} side="bodha" display="chart" />);

    const chart = screen.getByRole("list", { name: "Agreement of Bodha with the auditor, 95% Wilson intervals" });
    const first = within(chart).getByRole("listitem", { name: "E/M exact: 50%, 95% interval 9.5% to 90.5%" });
    expect(first).toHaveTextContent("50% (9.5%–90.5%)");
    expect(screen.getByText("Agreement")).toBeInTheDocument();
    expect(screen.getByText("95% interval")).toBeInTheDocument();
  });

  it("counts the direction of E/M disagreements and the ICD-10 F1", () => {
    render(<SampleSummaryPanel summary={SUMMARY} side="claim" display="chart" />);

    expect(screen.getByText("Final claim higher").nextSibling).toHaveTextContent("0 of 2");
    expect(screen.getByText("Final claim lower").nextSibling).toHaveTextContent("1 of 2");
    expect(screen.getByText("ICD-10 F1").nextSibling).toHaveTextContent("87.5%");
    expect(screen.getByText("2 notes coded")).toBeInTheDocument();
  });
});
