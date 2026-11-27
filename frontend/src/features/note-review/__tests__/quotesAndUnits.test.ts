import { describe, expect, it } from "vitest";
import type { Finding, NoteText } from "@/lib/api/types";
import { parseCodeList } from "@/lib/validation";
import { codeAfterLabel, codeLabel, quoteCheck, quoteStatus } from "../findings";

const TEXTS: NoteText[] = [
  { revision: 1, source: "document", text: "PHQ-9 score 4.\nGAD-7  score 2. Plan: increase metformin.", created_at: "2026-11-25T09:00:00Z" },
  { revision: 2, source: "addendum", text: "CKD stage 3a.", created_at: "2026-11-26T09:00:00Z" },
];

function finding(overrides: Partial<Finding>): Finding {
  return {
    kind: "code_review",
    key: "addon:96127",
    action: "add",
    title: "Depression screening",
    reasoning: "",
    code_before: null,
    code_after: "96127",
    evidence: [],
    severity: null,
    detail: {},
    default_choice: "accept",
    choice: "accept",
    allowed: ["accept", "keep"],
    departing_choices: [],
    override: null,
    override_needed: false,
    ...overrides,
  };
}

describe("quoteCheck", () => {
  it("finds every quote verbatim across the note and its addenda, ignoring case and spacing", () => {
    expect(quoteCheck(finding({ evidence: ["phq-9 score 4. gad-7 score 2.", "CKD stage 3a"] }), TEXTS)).toBe("found");
  });

  it("is not found when any quote is missing or only approximate", () => {
    expect(quoteCheck(finding({ evidence: ["PHQ-9 score 4", "PHQ-9 score 5"] }), TEXTS)).toBe("missing");
    expect(quoteCheck(finding({ evidence: ["increase metformin to 1000 mg"] }), TEXTS)).toBe("missing");
  });

  it("says nothing without quotes or without note text", () => {
    expect(quoteCheck(finding({ evidence: [] }), TEXTS)).toBeNull();
    expect(quoteCheck(finding({ evidence: ["  "] }), TEXTS)).toBeNull();
    expect(quoteCheck(finding({ evidence: ["PHQ-9 score 4"] }), [])).toBeNull();
  });

  it("shows a found quote as supported and a missing one as a warning", () => {
    expect(quoteStatus("found")).toEqual({ tone: "ok", label: "Quote found" });
    expect(quoteStatus("missing")).toEqual({ tone: "warn", label: "Quote not found" });
  });
});

describe("unit labels", () => {
  it("shows units after the code and modifiers only when there is more than one", () => {
    expect(codeLabel({ code: "96127", type: "CPT", modifiers: [], units: 2 })).toBe("96127 ×2");
    expect(codeLabel({ code: "97597", type: "CPT", modifiers: ["59"], units: 3 })).toBe("97597-59 ×3");
    expect(codeLabel({ code: "99214", type: "CPT", modifiers: ["25"], units: 1 })).toBe("99214-25");
    expect(codeLabel({ code: "99214", type: "CPT", modifiers: [] })).toBe("99214");
  });

  it("labels a suggested add-on with its units", () => {
    expect(codeAfterLabel(finding({ detail: { add_on: true, units: 2 } }))).toBe("96127 ×2");
    expect(codeAfterLabel(finding({ detail: { add_on: true, units: 1 } }))).toBe("96127");
    expect(codeAfterLabel(finding({ code_after: null, detail: { units: 2 } }))).toBeNull();
  });
});

describe("billed code entry", () => {
  it("accepts units in every written form, beside modifiers and ICD-10-CM placeholders", () => {
    const parsed = parseCodeList("96127x2, 96127 x 2, 96127×2, 96127 ×2, 97597-59x3, 99214-X2, O40.1XX0");
    expect(parsed.invalid).toEqual([]);
  });

  it("refuses units outside one to ninety-nine and codes that are not codes", () => {
    expect(parseCodeList("96127x0, 96127x100, 9612x2").invalid).toEqual(["96127x0", "96127x100", "9612x2"]);
  });
});
