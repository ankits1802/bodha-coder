import { describe, expect, it } from "vitest";
import { decisionOrder } from "../decisionFlow";
import { filterCounts, reviewGroups, supportedToAccept, visibleRows, type ReviewFilter } from "../reviewList";
import { filterChanges, historyChanges, reviewView } from "../reviewView";
import { finding, noteDetail } from "./fixtures";

const LOWER = finding({ kind: "em", key: "em", action: "lower", code_before: "99215", code_after: "99213", choice: "accept", allowed: ["accept", "keep"], departing_choices: ["keep"], amount_change: -96.4 });
const ADD_ON = finding({ kind: "code_review", key: "addon:96127", action: "add", code_before: null, code_after: "96127", choice: "accept", allowed: ["accept", "keep"], amount_change: 4.62 });
const NEW_DX = finding({ key: "dx:E11.65", action: "add", code_before: null, code_after: "E11.65", choice: "add", allowed: ["add", "skip"], amount_change: 0 });
const UNCONFIRMED = finding({ key: "dx:R69", action: "review", code_before: "R69", allowed: ["keep"] });
const NO_REASON = finding({ kind: "modifier", key: "mod:25", action: "remove", code_before: "99213", choice: "keep", allowed: ["accept", "keep"], override_needed: true, amount_change: 0 });
const SUPPORTED = finding({});
const MATCHES = finding({ kind: "em", key: "em-office", action: "keep", code_before: "99213", allowed: ["keep"] });
const QUERY = finding({ kind: "cdi_query", key: "cdiq-1", action: "ask", code_before: null, choice: "ask", allowed: ["ask", "skip"] });
const SUSPECTED = finding({ key: "hcc:18", action: "add", code_before: null, code_after: "E11.9", choice: "add", allowed: ["add", "skip"] });
const CRITICAL = finding({ kind: "audit_risk", key: "risk-1", action: "info", code_before: null, severity: "Critical", title: "Cloned exam" });
const MEDIUM = finding({ kind: "audit_risk", key: "risk-2", action: "info", code_before: null, severity: "Medium", title: "Thin history" });
const GAP = finding({ kind: "cdi_gap", key: "gap-1", action: "info", code_before: null, code_after: "E11.65", detail: { suggested_text: "Type 2 diabetes with hyperglycemia" } });
const LOOSE_GAP = finding({ kind: "cdi_gap", key: "gap-2", action: "info", code_before: null, code_after: "J45.40" });
const AUDIT_NOTE = finding({ kind: "audit_finding", key: "finding:0", action: "info", code_before: null });

const ALL = [SUPPORTED, AUDIT_NOTE, MEDIUM, QUERY, NEW_DX, LOOSE_GAP, ADD_ON, SUSPECTED, MATCHES, LOWER, GAP, CRITICAL, UNCONFIRMED, NO_REASON];
const keys = (filter: ReviewFilter, lane = "coder") => visibleRows(reviewGroups(noteDetail(ALL, { note: { lane } as never })), filter).map((row) => row.finding.key);

describe("one findings list", () => {
  it("puts what stops approval first, then changes by dollar size, then questions, risk adjustment and guidance", () => {
    expect(keys("all")).toEqual(["mod:25", "dx:R69", "em", "addon:96127", "dx:E11.65", "cdiq-1", "hcc:18", "risk-1", "risk-2", "gap-2", "finding:0"]);
  });

  it("treats a critical audit risk as blocking only while the note waits for compliance", () => {
    expect(keys("all", "compliance").slice(0, 3)).toEqual(["mod:25", "dx:R69", "risk-1"]);
  });

  it("folds the findings that only confirm the bill into one supported group", () => {
    const groups = reviewGroups(noteDetail(ALL));
    expect(groups.supported.map((item) => item.key)).toEqual(["dx:I10", "em-office"]);
    expect(supportedToAccept(groups).map((item) => item.key)).toEqual(["dx:I10", "em-office"]);
    const decided = reviewGroups(noteDetail([{ ...SUPPORTED, decided: true }, MATCHES]));
    expect(supportedToAccept(decided).map((item) => item.key)).toEqual(["em-office"]);
  });

  it("sets suggested wording under the finding it rewords and lists the rest as rows", () => {
    const rows = visibleRows(reviewGroups(noteDetail(ALL)), "all");
    expect(rows.find((row) => row.finding.key === "dx:E11.65")?.wording.map((gap) => gap.key)).toEqual(["gap-1"]);
    expect(rows.some((row) => row.finding.key === "gap-1")).toBe(false);
  });

  it("filters to one kind of finding and counts each kind for its chip", () => {
    expect(keys("changes")).toEqual(["mod:25", "dx:R69", "em", "addon:96127", "dx:E11.65"]);
    expect(keys("questions")).toEqual(["cdiq-1"]);
    expect(keys("risk")).toEqual(["hcc:18", "risk-1", "risk-2"]);
    expect(keys("guidance")).toEqual(["gap-2", "finding:0"]);
    expect(filterCounts(reviewGroups(noteDetail(ALL)))).toEqual({ all: 11, changes: 5, questions: 1, risk: 3, guidance: 2 });
  });

  it("moves through the findings with a choice to make in the order shown", () => {
    const rows = visibleRows(reviewGroups(noteDetail(ALL)), "all");
    expect(decisionOrder(rows)).toEqual(["mod:25", "em", "addon:96127", "dx:E11.65", "cdiq-1", "hcc:18"]);
  });

  it("puts a finding compliance sent back among the blocking items", () => {
    const groups = reviewGroups(noteDetail([LOWER, { ...ADD_ON, decide_again: true }]));
    expect(groups.blocking.map((row) => row.finding.key)).toEqual(["addon:96127"]);
  });
});

describe("filters in the address", () => {
  it("reads the filter, maps the old tab links to the nearest filter and opens History from either form", () => {
    expect(reviewView({ filter: "questions", tab: null, history: null })).toEqual({ filter: "questions", history: false });
    expect(reviewView({ filter: null, tab: "codes", history: null }).filter).toBe("changes");
    expect(reviewView({ filter: null, tab: "wording", history: null }).filter).toBe("guidance");
    expect(reviewView({ filter: null, tab: "audit", history: null }).filter).toBe("risk");
    expect(reviewView({ filter: null, tab: "risk", history: null }).filter).toBe("risk");
    expect(reviewView({ filter: null, tab: "history", history: null })).toEqual({ filter: "all", history: true });
    expect(reviewView({ filter: null, tab: null, history: "1" })).toEqual({ filter: "all", history: true });
    expect(reviewView({ filter: "nonsense", tab: "nonsense", history: null })).toEqual({ filter: "all", history: false });
  });

  it("writes the filter and the drawer back without the old tab", () => {
    const fromTab = reviewView({ filter: null, tab: "codes", history: null });
    expect(historyChanges(fromTab, true)).toEqual({ filter: "changes", tab: null, history: "1" });
    expect(filterChanges(fromTab, "all")).toEqual({ filter: null, tab: null, history: null });
    expect(historyChanges(reviewView({ filter: null, tab: "history", history: null }), false)).toEqual({ filter: null, tab: null, history: null });
  });
});
