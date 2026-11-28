import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { HqOverview } from "@/lib/api/types";
import { OverviewStats } from "../HqOverviewScreen";

const OVERVIEW: HqOverview = {
  organizations: 3,
  practices: 8,
  people: 41,
  read_last_24h: 120,
  tokens_last_24h: 5000,
  cost_last_24h_usd: 1.5,
  unpriced_last_24h: 0,
  failed_last_24h: 2,
  waiting: 6,
  running: 1,
  month: { from: "2026-11-01", to: "2026-11-28", cost_usd: 42, unpriced_analyses: 2 },
};

function stats(): HTMLElement {
  return screen.getByRole("region", { name: "Platform" });
}

describe("HQ overview figures", () => {
  it("opens the organizations, the live practices and this month's spend", () => {
    render(<OverviewStats overview={OVERVIEW} linked />);
    const links = within(stats()).getAllByRole("link");
    expect(links.map((link) => [(link.textContent ?? "").replace(/\s+/g, " ").trim(), link.getAttribute("href")])).toEqual([
      ["Organizations, 3", "/hq/organizations"],
      ["Practices, 8", "/hq/practices?status=live"],
      ["Model cost this month, $42.00, 2 without a price", "/hq/spend?from=2026-11-01&to=2026-11-28"],
    ]);
    expect(screen.getByRole("link", { name: "Organizations, 3" })).toBeInTheDocument();
  });

  it("leaves figures with no list behind them as text", () => {
    render(<OverviewStats overview={OVERVIEW} linked />);
    for (const label of ["People", "Read in 24 h", "Waiting", "Could not read", "Model tokens in 24 h", "Model cost in 24 h"]) {
      expect(within(stats()).getByText(label).closest("a")).toBeNull();
    }
  });

  it("links nothing when the viewer cannot open HQ", () => {
    render(<OverviewStats overview={OVERVIEW} linked={false} />);
    expect(within(stats()).queryAllByRole("link")).toEqual([]);
    expect(within(stats()).getByText("Organizations")).toBeInTheDocument();
  });
});
