import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ClaimEstimates } from "@/lib/api/types";
import { ClaimCodes, EstimateSummary } from "../components/ClaimEstimate";

const ESTIMATE: ClaimEstimates = {
  release: "RVU26D",
  setting: "non_facility",
  billed: { total: 202.41, lines: [{ code: "99215", amount: 192.39 }, { code: "96127 ×2", amount: 10.02 }], unpriced: [] },
  claim: {
    total: 145.63,
    lines: [
      { code: "99214", amount: 135.61 },
      { code: "96127 ×2", amount: 10.02 },
      { code: "99417", amount: null },
    ],
    unpriced: ["99417"],
  },
  difference: -56.78,
};

describe("ClaimCodes", () => {
  it("shows the estimated national amount beside each procedure line and a dash when there is none", () => {
    const { container } = render(<ClaimCodes claim={["99214", "96127 ×2", "99417", "E11.65"]} estimate={ESTIMATE} />);

    expect(screen.getByText("Est. $135.61")).toBeInTheDocument();
    expect(screen.getByText("Est. $10.02")).toBeInTheDocument();
    expect(screen.getByText("Est. —")).toBeInTheDocument();
    expect(container.textContent).toContain("E11.65");
    expect(screen.getAllByText(/^Est\./)).toHaveLength(3);
  });

  it("shows the codes alone when there is no estimate", () => {
    render(<ClaimCodes claim={["99214"]} estimate={null} />);

    expect(screen.getByText("99214")).toBeInTheDocument();
    expect(screen.queryByText(/^Est\./)).toBeNull();
  });
});

describe("EstimateSummary", () => {
  it("labels the billed, claim and difference figures as Medicare national estimates", () => {
    render(<EstimateSummary estimate={ESTIMATE} />);

    expect(screen.getByText("Estimated Medicare national")).toBeInTheDocument();
    expect(screen.getByText("Billed $202.41")).toBeInTheDocument();
    expect(screen.getByText("Claim $145.63")).toBeInTheDocument();
    expect(screen.getByText("Difference -$56.78")).toBeInTheDocument();
  });
});
