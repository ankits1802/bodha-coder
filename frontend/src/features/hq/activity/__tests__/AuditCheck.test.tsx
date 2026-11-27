import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AuditChain, AuditVerification } from "@/lib/api/types";
import { changeLines } from "../activityModel";
import { AuditCheck } from "../AuditCheck";

const ACTIVITY: AuditChain = {
  chain: "activity",
  practice_id: null,
  practice_name: null,
  checked: 40,
  head_seq: 40,
  head_hash: "a".repeat(64),
  intact: true,
  broken_seq: null,
  broken_id: null,
  problem: null,
};

const LAKESIDE: AuditChain = { ...ACTIVITY, chain: "access_log", practice_id: "p1", practice_name: "Lakeside Primary Care", checked: 1200 };

function verification(chains: AuditChain[]): AuditVerification {
  return { checked_at: "2026-11-28T15:00:00Z", intact: chains.every((chain) => chain.intact), chains };
}

describe("AuditCheck", () => {
  it("says how many chains and entries were found intact", () => {
    render(<AuditCheck result={verification([ACTIVITY, LAKESIDE])} error={null} />);
    expect(screen.getByText("2 chains intact · 1,240 entries")).toBeInTheDocument();
  });

  it("names each broken chain with its first broken entry and what is wrong", () => {
    const broken: AuditChain = { ...LAKESIDE, intact: false, checked: 11, broken_seq: 12, broken_id: "row-12", problem: "changed row" };
    const missing: AuditChain = { ...ACTIVITY, intact: false, checked: 2, broken_seq: 4, broken_id: "row-4", problem: "missing rows" };
    render(<AuditCheck result={verification([missing, broken])} error={null} />);
    expect(screen.getByText("2 broken")).toBeInTheDocument();
    expect(screen.getByText("HQ activity: entry 4 · Entries missing")).toBeInTheDocument();
    expect(screen.getByText("Lakeside Primary Care: entry 12 · Entry changed")).toBeInTheDocument();
  });

  it("shows nothing before a check has run", () => {
    const { container } = render(<AuditCheck result={null} error={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("changeLines", () => {
  it("writes each practice change as its field before and after", () => {
    expect(
      changeLines([
        { field: "seats", before: 10, after: 12 },
        { field: "renews_on", before: null, after: "2027-03-31" },
      ]),
    ).toEqual(["Seats: 10 → 12", "Renews on: Not set → 2027-03-31"]);
    expect(changeLines(null)).toEqual([]);
  });
});
