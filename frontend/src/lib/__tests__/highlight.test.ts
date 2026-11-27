import { describe, expect, it } from "vitest";
import { containsQuote, highlightSegments } from "@/lib/highlight";

describe("containsQuote", () => {
  it("finds a quote verbatim after folding case and whitespace", () => {
    expect(containsQuote("Assessment:\n  Hypertension above goal.", "hypertension ABOVE goal")).toBe(true);
    expect(containsQuote("Hypertension above goal.", "Hypertension at goal")).toBe(false);
    expect(containsQuote("Hypertension", "   ")).toBe(false);
  });
});

describe("highlightSegments", () => {
  it("marks an exact quote and keeps the surrounding text", () => {
    const text = "BP 148/88. eGFR 38, creatinine 1.5.";

    expect(highlightSegments(text, [{ quote: "eGFR 38", tone: "warn" }])).toEqual([
      { text: "BP 148/88. ", tone: null },
      { text: "eGFR 38", tone: "warn" },
      { text: ", creatinine 1.5.", tone: null },
    ]);
  });

  it("ignores case and runs of whitespace but never matches approximately", () => {
    const text = "eGFR  38,\ncreatinine 1.5.";

    expect(highlightSegments(text, [{ quote: "egfr 38, creatinine", tone: "warn" }])).toEqual([
      { text: "eGFR  38,\ncreatinine", tone: "warn" },
      { text: " 1.5.", tone: null },
    ]);
    expect(highlightSegments(text, [{ quote: "eGFR 39", tone: "warn" }])).toEqual([{ text, tone: null }]);
    expect(highlightSegments(text, [{ quote: "eGFR38", tone: "warn" }])).toEqual([{ text, tone: null }]);
  });

  it("marks every occurrence of a quote", () => {
    expect(highlightSegments("CKD, stable. CKD stage?", [{ quote: "CKD", tone: "bad" }])).toEqual([
      { text: "CKD", tone: "bad" },
      { text: ", stable. ", tone: null },
      { text: "CKD", tone: "bad" },
      { text: " stage?", tone: null },
    ]);
  });

  it("keeps the earlier quote when two quotes overlap", () => {
    const marks = [
      { quote: "diabetes with hyperglycemia", tone: "warn" as const },
      { quote: "Type 2 diabetes", tone: "ok" as const },
    ];

    expect(highlightSegments("Type 2 diabetes with hyperglycemia", marks)).toEqual([
      { text: "Type 2 diabetes", tone: "ok" },
      { text: " with hyperglycemia", tone: null },
    ]);
  });

  it("ignores blank quotes and trims quote whitespace", () => {
    expect(highlightSegments("Hypertension", [{ quote: "   ", tone: "ok" }])).toEqual([{ text: "Hypertension", tone: null }]);
    expect(highlightSegments("Hypertension", [{ quote: " Hypertension ", tone: "ok" }])).toEqual([
      { text: "Hypertension", tone: "ok" },
    ]);
  });
});
