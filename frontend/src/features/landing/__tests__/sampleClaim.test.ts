import { describe, expect, it } from "vitest";
import { containsQuote } from "@/lib/highlight";
import { claimCodes, nextOpen, openCount } from "../sample/claim";
import { SAMPLE_NOTES } from "../sample/samples";

function sample(key: string) {
  const found = SAMPLE_NOTES.find((note) => note.key === key);
  if (!found) throw new Error(`no sample note ${key}`);
  return found;
}

describe("sample notes", () => {
  it("are labelled as samples and quote only sentences that are in their note", () => {
    for (const note of SAMPLE_NOTES) {
      expect(note.header.startsWith("Sample note")).toBe(true);
      for (const finding of note.findings) {
        expect(finding.evidence.length).toBeGreaterThan(0);
        for (const quote of finding.evidence) expect(containsQuote(note.note, quote)).toBe(true);
      }
    }
  });

  it("change only codes that were billed, in the list of their kind", () => {
    for (const note of SAMPLE_NOTES) {
      for (const finding of note.findings) {
        const billed = finding.kind === "procedure" ? note.billed.procedures : note.billed.diagnoses;
        if (finding.before !== null) expect(billed).toContain(finding.before);
        expect(billed).not.toContain(finding.after);
      }
    }
  });

  it("show a level billed too high, an add-on missed and a diagnosis coded without its detail", () => {
    expect(SAMPLE_NOTES.map((note) => [note.tab, note.findings.map((finding) => `${finding.before ?? "add"}>${finding.after}`)])).toEqual([
      ["Billed too high", ["99214>99213", "J01.90>J01.00"]],
      ["Billed too low", ["99213>99214", "add>G2211"]],
      ["HCC capture", ["E11.9>E11.22", "N18.9>N18.31", "I10>I12.9"]],
    ]);
  });
});

describe("claimCodes", () => {
  it("keeps the billed codes while nothing is accepted", () => {
    const note = sample("follow-up");
    expect(claimCodes(note.billed, note.findings, {})).toEqual(note.billed);
    expect(claimCodes(note.billed, note.findings, { em: "reject", longitudinal: "reject" })).toEqual(note.billed);
  });

  it("replaces a changed code in place and adds an add-on after the visit", () => {
    const note = sample("follow-up");
    expect(claimCodes(note.billed, note.findings, { em: "accept", longitudinal: "accept" })).toEqual({
      procedures: ["99214", "G2211"],
      diagnoses: ["E11.9", "I10", "Z79.84"],
    });
  });

  it("applies each accepted change and leaves rejected ones billed", () => {
    const note = sample("kidney");
    expect(claimCodes(note.billed, note.findings, { diabetes: "accept", stage: "accept", hypertension: "reject" })).toEqual({
      procedures: ["99214"],
      diagnoses: ["E11.22", "N18.31", "I10", "Z79.84"],
    });
  });
});

describe("openCount and nextOpen", () => {
  const note = sample("kidney");

  it("counts the findings without a decision", () => {
    expect(openCount(note.findings, {})).toBe(3);
    expect(openCount(note.findings, { stage: "reject" })).toBe(2);
    expect(openCount(note.findings, { diabetes: "accept", stage: "reject", hypertension: "accept" })).toBe(0);
  });

  it("moves to the next open finding, wrapping to the first, and to nothing when all are decided", () => {
    expect(nextOpen(note.findings, { diabetes: "accept" }, "diabetes")).toBe("stage");
    expect(nextOpen(note.findings, { hypertension: "accept" }, "hypertension")).toBe("diabetes");
    expect(nextOpen(note.findings, { diabetes: "accept", hypertension: "reject" }, "hypertension")).toBe("stage");
    expect(nextOpen(note.findings, { diabetes: "accept", stage: "accept", hypertension: "reject" }, "stage")).toBeNull();
  });
});
