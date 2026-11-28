import { describe, expect, it } from "vitest";
import type { BillingRow, ClaimColumn } from "@/lib/api/types";
import { claimNote, isSendable, missingLabel, missingSummary, offersDetails, sendableIds } from "../claimStatus";
import { claimRow } from "./claimFixtures";

function column(change: Partial<ClaimColumn>): ClaimColumn {
  return { status: "ready", at: null, reasons: [], missing: [], ...change };
}

describe("claim status words", () => {
  it("names each missing item, a charge by its code", () => {
    expect(missingLabel("practice.zip")).toBe("Practice ZIP+4");
    expect(missingLabel("payer.id")).toBe("Payer ID");
    expect(missingLabel("details")).toBe("Patient and subscriber");
    expect(missingLabel("charge:99214")).toBe("Charge for 99214");
    expect(missingLabel("something.new")).toBe("something.new");
  });

  it("lists at most three missing items and counts the rest", () => {
    expect(missingSummary(["payer", "details"])).toBe("Payer, Patient and subscriber");
    expect(missingSummary(["connection", "payer", "details", "charge:99214", "charge:96127"])).toBe(
      "Clearinghouse, Payer, Patient and subscriber and 2 more",
    );
  });

  it("explains a missing claim by what is missing and a rejection by its first reason, capitalised", () => {
    expect(claimNote(column({ status: "missing", missing: ["payer.id"] }))).toBe("Payer ID");
    const reasons = [{ code: "A7:562:85", text: "rejected for invalid information (status 562)" }];
    expect(claimNote(column({ status: "rejected", reasons }))).toBe("Rejected for invalid information (status 562)");
    expect(claimNote(column({ status: "accepted", reasons }))).toBeNull();
  });

  it("offers details only while the claim can still be fixed", () => {
    expect(offersDetails(column({ status: "missing" }))).toBe(true);
    expect(offersDetails(column({ status: "rejected" }))).toBe(true);
    expect(offersDetails(column({ status: "sent" }))).toBe(false);
    expect(offersDetails(null)).toBe(false);
  });
});

describe("claims to send", () => {
  it("sends ready claims and fixed rejections, never held or incomplete ones", () => {
    const rows: BillingRow[] = [
      claimRow("ready", column({ status: "ready" })),
      claimRow("fixed", column({ status: "rejected" })),
      claimRow("still-missing", column({ status: "rejected", missing: ["details"] })),
      claimRow("sent", column({ status: "sent" })),
      { ...claimRow("held", column({ status: "ready" })), held: true },
      claimRow("csv", null),
    ];
    expect(sendableIds(rows)).toEqual(["ready", "fixed"]);
    expect(isSendable(claimRow("failed", column({ status: "failed" })))).toBe(true);
  });
});
