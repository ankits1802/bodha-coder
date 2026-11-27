import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { getClaimChecks } from "@/lib/api/claimChecks";
import { ApiError } from "@/lib/api/errors";
import type { ClaimChecks } from "@/lib/api/types";
import { ClaimChecksPanel } from "../ClaimChecksPanel";
import { claimCheckItems } from "../claimCheckItems";

vi.mock("@/lib/api/claimChecks", () => ({ getClaimChecks: vi.fn() }));

const CHECKS: ClaimChecks = {
  ncci: { quarter: "2026Q4", covers: true },
  edits: [
    { kind: "ptp", column1: "20610", column2: "99214", modifier_allowed: true, bypassed_by: null },
    { kind: "ptp", column1: "11042", column2: "99213", modifier_allowed: true, bypassed_by: "59" },
    { kind: "ptp", column1: "36415", column2: "36591", modifier_allowed: false, bypassed_by: null },
    { kind: "mue", code: "96127", units: 5, limit: 2, mai: 3 },
    { kind: "aoc", code: "99292", primaries: ["99291"] },
  ],
  payer: { name: "Medicare Part B", plan_type: "medicare" },
  payer_flags: [{ rule: "complexity_with_25", severity: "denial", codes: ["99214-25", "G2211"] }],
};

function rows(): HTMLElement[] {
  return within(screen.getByRole("list", { name: "Claim checks" })).getAllByRole("listitem");
}

describe("ClaimChecksPanel", () => {
  it("lists each edit and payer flag with a dot and a word", async () => {
    vi.mocked(getClaimChecks).mockResolvedValue(CHECKS);
    render(<ClaimChecksPanel noteId="note-1" claim={["99214", "20610"]} />);

    expect(await screen.findByText("Bypassed with 59")).toBeInTheDocument();
    const listed = rows();
    expect(listed).toHaveLength(6);
    expect(listed[0]).toHaveTextContent("2061099214Modifier allowedCannot be billed together");
    expect(listed[1]).toHaveTextContent("1104299213Bypassed with 59");
    expect(listed[2]).toHaveTextContent("3641536591Cannot be billed together");
    expect(listed[2]).not.toHaveTextContent("Modifier allowed");
    expect(listed[3]).toHaveTextContent("96127 ×5Units over limit (MUE 2)");
    expect(listed[4]).toHaveTextContent("99292Add-on without its primary");
    expect(listed[5]).toHaveTextContent("99214-25G2211Complexity add-on not paid with 25");
    expect(getClaimChecks).toHaveBeenCalledWith("note-1");
  });

  it("says when the claim is clean and the payer is not set", async () => {
    vi.mocked(getClaimChecks).mockResolvedValue({ ...CHECKS, edits: [], payer: null, payer_flags: [] });
    render(<ClaimChecksPanel noteId="note-2" claim={["99213"]} />);

    expect(await screen.findByText("No claim edits")).toBeInTheDocument();
    expect(screen.getByText("Payer not set")).toBeInTheDocument();
  });

  it("shows the error with a retry", async () => {
    vi.mocked(getClaimChecks).mockRejectedValue(new ApiError(404, "not_found", "note not found"));
    render(<ClaimChecksPanel noteId="note-3" claim={[]} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Note not found");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("shows loading until the checks arrive", () => {
    vi.mocked(getClaimChecks).mockReturnValue(new Promise(() => {}));
    render(<ClaimChecksPanel noteId="note-4" claim={[]} />);

    expect(screen.getByText("Checking the claim")).toBeInTheDocument();
  });
});

describe("claimCheckItems", () => {
  it("names the quarter when the date of service is outside the loaded NCCI tables", () => {
    const items = claimCheckItems({ ...CHECKS, ncci: { quarter: "2026Q4", covers: false }, edits: [], payer_flags: [] });
    expect(items.map((item) => [item.tone, item.status])).toEqual([["neutral", "NCCI 2026Q4 not loaded for this date"]]);
  });

  it("gives denials the bad tone, risks the warning tone and reminders a neutral tone", () => {
    const items = claimCheckItems({
      ...CHECKS,
      edits: [],
      payer_flags: [
        { rule: "g2211_replaced", severity: "denial", codes: ["G2211"] },
        { rule: "level_downcode_risk", severity: "risk", codes: ["99214"] },
        { rule: "nursing_initial_once", severity: "reminder", codes: ["99306"] },
      ],
    });
    expect(items.map((item) => [item.tone, item.status])).toEqual([
      ["bad", "G2211 replaced by modifier B1"],
      ["warn", "Likely downcode, document MDM"],
      ["neutral", "Initial visit once per stay"],
    ]);
  });
});
