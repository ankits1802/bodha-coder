import { describe, expect, it } from "vitest";
import type { ComplianceRow, LaneReason } from "@/lib/api/types";
import { countByKind, inKind, kindOf } from "../complianceKinds";

function row(id: string, laneReason: LaneReason | null, headline: string): ComplianceRow {
  return {
    id,
    patient_name: "Ruth Abernathy",
    provider_name: "Samuel Okafor",
    service_date: "2026-11-24",
    status: "ready",
    lane: "compliance",
    lane_reason: laneReason,
    headline,
    place_code: "31",
    visit_type: "Established patient",
    flag_reason: null,
    flagged_by: null,
    flagged_by_name: null,
    due_at: "2026-11-26T18:00:00Z",
    file_name: "ruth.pdf",
    assigned_to: null,
    payer: null,
    assignee_name: null,
    billed: ["99310"],
    suggested: ["99308"],
    em_action: "lower",
    impact_cents: null,
  };
}

describe("compliance kinds", () => {
  const rows = [
    row("a", "levels_too_high", "2 levels too high"),
    row("b", "flagged", "Reworded headline"),
    row("c", "audit_risk", "Anything"),
    row("d", "levels_too_high", "3 levels too high"),
  ];

  it("classifies by the lane reason, whatever the headline says", () => {
    expect(rows.map(kindOf)).toEqual(["too_high", "flagged", "risk", "too_high"]);
  });

  it("counts and filters each tab", () => {
    expect(countByKind(rows)).toEqual({ all: 4, too_high: 2, risk: 1, flagged: 1 });
    expect(rows.filter((item) => inKind(item, "flagged")).map((item) => item.id)).toEqual(["b"]);
    expect(rows.filter((item) => inKind(item, "all"))).toHaveLength(4);
  });
});
