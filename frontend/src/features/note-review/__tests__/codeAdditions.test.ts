import { describe, expect, it } from "vitest";
import type { Finding } from "@/lib/api/types";
import { codeChangeCount, formatRiskScore, isCodeFinding, measureStatus, riskSummary, suspectedConditions } from "../findings";

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

const summary = finding({
  key: "hcc",
  action: "info",
  title: "Risk adjustment",
  code_before: null,
  detail: {
    model: "CMS-HCC V28",
    payment_year: "2027",
    available: true,
    segment: "Community, non-dual, aged",
    score_billed: 0.638,
    score_documented: 0.824,
    categories: [
      { hcc: "HCC37", label: "Diabetes with Chronic Complications", status: "missed", codes: ["E11.22"], factor: 0.166 },
      { hcc: "HCC99", label: "Unknown", status: "invented", codes: [], factor: 1 },
    ],
  },
});
const suspected = finding({ key: "hcc:N18.32", action: "ask", choice: "ask", code_before: null, title: "eGFR 38. Clarify?" });
const modifier = finding({ kind: "modifier", key: "modifier:25", action: "add", code_before: "99214", code_after: "99214-25" });
const addOn = finding({ kind: "code_review", key: "addon:96127", action: "add", code_before: null, code_after: "96127" });

describe("risk adjustment findings", () => {
  it("reads the summary and drops rows with an unknown status", () => {
    const parsed = riskSummary([summary, suspected]);
    expect(parsed?.scoreBilled).toBe(0.638);
    expect(parsed?.scoreDocumented).toBe(0.824);
    expect(parsed?.categories).toEqual([
      { hcc: "HCC37", label: "Diabetes with Chronic Complications", status: "missed", codes: ["E11.22"], factor: 0.166 },
    ]);
  });

  it("has no summary when the check did not run", () => {
    expect(riskSummary([modifier])).toBeNull();
  });

  it("keeps risk items out of the Codes tab and lists suspected conditions apart", () => {
    expect([summary, suspected, modifier, addOn].filter(isCodeFinding).map((item) => item.key)).toEqual([
      "modifier:25",
      "addon:96127",
    ]);
    expect(suspectedConditions([summary, suspected]).map((item) => item.key)).toEqual(["hcc:N18.32"]);
  });

  it("writes scores with three decimals", () => {
    expect(formatRiskScore(0.5)).toBe("0.500");
    expect(formatRiskScore(null)).toBe("—");
  });
});

describe("code changes", () => {
  it("counts modifier and add-on suggestions", () => {
    expect(codeChangeCount([modifier, addOn, summary])).toBe(2);
  });
});

describe("measureStatus", () => {
  it("reads only the statuses the server sends", () => {
    expect(measureStatus(finding({ kind: "mips", detail: { status: "met" } }))).toBe("met");
    expect(measureStatus(finding({ kind: "mips", detail: { status: "not_applicable" } }))).toBe("not_applicable");
    expect(measureStatus(finding({ kind: "mips", detail: {} }))).toBeNull();
  });
});
