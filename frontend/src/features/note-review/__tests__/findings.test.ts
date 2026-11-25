import { describe, expect, it } from "vitest";
import type { Finding } from "@/lib/api/types";
import { highlightTone, marksFor, openQuestions } from "../findings";

function finding(overrides: Partial<Finding>): Finding {
  return {
    kind: "diagnosis",
    key: "dx:I10",
    action: "keep",
    title: "Hypertension",
    reasoning: "",
    code_before: "I10",
    code_after: null,
    evidence: [],
    severity: null,
    detail: {},
    default_choice: "keep",
    choice: "keep",
    allowed: ["keep"],
    ...overrides,
  };
}

describe("highlightTone", () => {
  it("marks supported and accepted changes green", () => {
    expect(highlightTone({ kind: "diagnosis", action: "keep" })).toBe("ok");
    expect(highlightTone({ kind: "diagnosis", action: "add" })).toBe("ok");
    expect(highlightTone({ kind: "em", action: "lower" })).toBe("ok");
    expect(highlightTone({ kind: "em", action: "raise" })).toBe("ok");
    expect(highlightTone({ kind: "diagnosis", action: "replace" })).toBe("ok");
  });

  it("marks what needs detail orange", () => {
    expect(highlightTone({ kind: "diagnosis", action: "ask" })).toBe("warn");
    expect(highlightTone({ kind: "code_review", action: "review" })).toBe("warn");
    expect(highlightTone({ kind: "cdi_gap", action: "info" })).toBe("warn");
  });

  it("marks what is not supported red", () => {
    expect(highlightTone({ kind: "diagnosis", action: "remove" })).toBe("bad");
  });

  it("does not highlight audit notes or findings that do not apply", () => {
    expect(highlightTone({ kind: "audit_risk", action: "info" })).toBeNull();
    expect(highlightTone({ kind: "em", action: "not_applicable" })).toBeNull();
  });
});

describe("marksFor", () => {
  it("turns every evidence quote into a mark with the finding tone", () => {
    const findings = [
      finding({ action: "keep", evidence: ["Hypertension, above goal"] }),
      finding({ key: "dx:N18.30", action: "ask", evidence: ["CKD, stable", "eGFR 38"] }),
      finding({ key: "risk-1", kind: "audit_risk", action: "info", evidence: ["ignored"] }),
    ];
    expect(marksFor(findings)).toEqual([
      { quote: "Hypertension, above goal", tone: "ok" },
      { quote: "CKD, stable", tone: "warn" },
      { quote: "eGFR 38", tone: "warn" },
    ]);
  });
});

describe("openQuestions", () => {
  it("keeps only question findings still set to ask", () => {
    const asked = finding({ key: "dx:N18.30", action: "ask", choice: "ask" });
    const query = finding({ key: "cdiq-1", kind: "cdi_query", action: "ask", choice: "ask", code_before: null });
    const skipped = finding({ key: "cdiq-2", kind: "cdi_query", action: "ask", choice: "skip", code_before: null });
    const kept = finding({ key: "dx:E11.9", action: "ask", choice: "keep" });
    expect(openQuestions([asked, query, skipped, kept]).map((item) => item.key)).toEqual(["dx:N18.30", "cdiq-1"]);
  });
});
