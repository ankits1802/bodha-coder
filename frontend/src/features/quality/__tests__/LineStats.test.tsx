import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EvalRunView, EvalRuns, EvalSummary, Rate } from "@/lib/api/types";
import { LineStats } from "../components/LineStats";
import { lineRates } from "../qualityModel";

const ONE_OF_ONE: Rate = { successes: 1, trials: 1, value: 1, low: 0.206549, high: 1 };
const NONE: Rate = { successes: 0, trials: 0, value: null, low: null, high: null };

const CURRENT: EvalSummary = {
  cases: 2,
  scored: 2,
  failed: 0,
  procedures: ONE_OF_ONE,
  add_ons: NONE,
  units: { successes: 0, trials: 1, value: 0, low: 0, high: 0.793451 },
  place_of_service: { successes: 2, trials: 2, value: 1, low: 0.34238, high: 1 },
  case_counts: { em: 2, icd: 2, modifiers: 2, procedures: 1, add_ons: 0, units: 1, place_of_service: 2 },
};

function run(id: string, status: EvalRunView["status"], summary: EvalSummary): EvalRunView {
  return { id, status, model: "gemini", prompt_version: "2026.11.7", requested_at: null, finished_at: null, summary, change: null };
}

function cells(): HTMLElement[] {
  return Array.from(screen.getByRole("region", { name: "Claim lines in the latest evaluation" }).children) as HTMLElement[];
}

describe("LineStats", () => {
  it("shows each claim line metric of the latest finished run with its interval and case count", () => {
    const data: EvalRuns = { cases: 2, runs: [run("queued", "queued", {}), run("done", "done", CURRENT)] };
    render(<LineStats data={data} />);

    const [procedures, addOns, units, place] = cells();
    expect(procedures).toHaveTextContent("Procedure lines, 100%, 20.7%–100% · 1 case");
    expect(addOns).toHaveTextContent("Add-on codes, —, 0 cases");
    expect(units).toHaveTextContent("Units, 0%, 0%–79.3% · 1 case");
    expect(place).toHaveTextContent("Place of service, 100%, 34.2%–100% · 2 cases");
  });

  it("keeps a run from before claim line scoring readable", () => {
    const older: EvalSummary = { cases: 1, scored: 1, failed: 0, em: ONE_OF_ONE, icd_f1: 1, modifiers: ONE_OF_ONE };
    render(<LineStats data={{ cases: 1, runs: [run("older", "done", older)] }} />);

    expect(cells().map((cell) => cell.textContent)).toEqual(["Procedure lines, —", "Add-on codes, —", "Units, —", "Place of service, —"]);
  });

  it("reads no metric when no run has finished", () => {
    expect(lineRates(undefined).map((line) => [line.key, line.rate, line.cases])).toEqual([
      ["procedures", null, null],
      ["add_ons", null, null],
      ["units", null, null],
      ["place_of_service", null, null],
    ]);
  });
});
