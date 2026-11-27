import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ClaimEstimates, ClaimPointers } from "@/lib/api/types";
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

const POINTERS: ClaimPointers = {
  diagnoses: [
    { code: "E11.65", letter: "A" },
    { code: "N18.30", letter: "B" },
  ],
  lines: [
    { code: "99214", label: "99214", pointers: ["E11.65", "N18.30"], stored: false },
    { code: "96127", label: "96127 ×2", pointers: ["N18.30"], stored: true },
  ],
};
const LINKED_CLAIM = ["99214", "96127 ×2", "E11.65", "N18.30"];

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

  it("letters the diagnoses and opens the pointer editor from a procedure line", () => {
    const onEdit = vi.fn();
    render(<ClaimCodes claim={LINKED_CLAIM} estimate={null} pointers={POINTERS} onEdit={onEdit} />);

    const visit = screen.getByRole("button", { name: "99214 AB, diagnoses E11.65, N18.30" });
    const screening = screen.getByRole("button", { name: "96127 ×2 B, diagnoses N18.30" });
    expect(visit).toHaveTextContent("99214 AB");
    expect(screening).toHaveTextContent("96127 ×2 B");
    fireEvent.click(screening);
    expect(onEdit).toHaveBeenCalledWith(POINTERS.lines[1]);
  });

  it("shows the pointers without buttons when the claim cannot be changed", () => {
    const { container } = render(<ClaimCodes claim={LINKED_CLAIM} estimate={null} pointers={POINTERS} onEdit={null} />);

    expect(screen.queryByRole("button")).toBeNull();
    expect(container.textContent).toBe("99214AB96127 ×2BAE11.65BN18.30");
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
