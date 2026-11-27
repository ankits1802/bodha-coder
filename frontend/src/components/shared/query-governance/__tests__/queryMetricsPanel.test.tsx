import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { getQueryMetrics } from "@/lib/api/queryGovernance";
import type { QueryMetricsReport } from "@/lib/api/types";
import { QueryMetricsPanel } from "../QueryMetricsPanel";

vi.mock("@/lib/api/queryGovernance", () => ({ getQueryMetrics: vi.fn(), downloadAddendum: vi.fn() }));

const VARGA = {
  notes: 1,
  queries: 3,
  per_100_notes: 300,
  response_rate: 0.6667,
  median_hours: 3,
  agree_rate: 0.5,
  repeat_rate: 0.3333,
};

const REPORT: QueryMetricsReport = {
  days: 30,
  total: { ...VARGA, notes: 3, per_100_notes: 100 },
  providers: [
    { provider_id: "p1", provider_name: "Elena Varga", ...VARGA },
    {
      provider_id: "p2",
      provider_name: "Omar Haddad",
      notes: 2,
      queries: 0,
      per_100_notes: 0,
      response_rate: null,
      median_hours: null,
      agree_rate: null,
      repeat_rate: null,
    },
  ],
};

describe("QueryMetricsPanel", () => {
  it("shows each provider's query rates and the practice total", async () => {
    vi.mocked(getQueryMetrics).mockResolvedValue(REPORT);
    render(<QueryMetricsPanel days={30} />);

    const table = await screen.findByRole("table", { name: "Provider queries by provider in this period" });
    const rows = within(table).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Elena Varga330066.7%3 h50%33.3%");
    expect(rows[2]).toHaveTextContent("Omar Haddad00————");
    expect(rows[3]).toHaveTextContent("All providers310066.7%3 h50%33.3%");
    expect(getQueryMetrics).toHaveBeenCalledWith(30);
  });

  it("says so when no provider was queried in the period", async () => {
    vi.mocked(getQueryMetrics).mockResolvedValue({
      days: 7,
      total: { ...VARGA, queries: 0, per_100_notes: 0, response_rate: null, median_hours: null, agree_rate: null, repeat_rate: null },
      providers: [],
    });
    render(<QueryMetricsPanel days={7} />);

    expect(await screen.findByText("No provider queries in this period")).toBeInTheDocument();
  });

  it("shows the error with a retry when the metrics cannot load", async () => {
    vi.mocked(getQueryMetrics).mockRejectedValue(new Error("Network down"));
    render(<QueryMetricsPanel days={14} />);

    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
