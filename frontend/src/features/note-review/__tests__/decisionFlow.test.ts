import { describe, expect, it } from "vitest";
import type { Finding, NoteDetail, QueuePage, QueueRow } from "@/lib/api/types";
import { choiceFor, codeFindings, decisionOrder, nextInOrder, questionFindings, withChoice } from "../decisionFlow";
import { currentFindingKey } from "../useFindingFocus";
import { neighboursIn, withoutNote } from "../useNoteData";

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

const EM = finding({ kind: "em", key: "em", action: "lower", code_before: "99215", code_after: "99214", choice: "accept", allowed: ["accept", "keep"] });
const SUPPORTED = finding({});
const ADDED = finding({ key: "dx:E11.65", action: "add", code_before: null, code_after: "E11.65", choice: "add", allowed: ["add", "skip"] });
const QUERY = finding({ kind: "cdi_query", key: "cdiq-1", action: "ask", code_before: null, choice: "ask", allowed: ["ask", "skip"] });
const FINDINGS = [ADDED, QUERY, SUPPORTED, EM];

function row(id: string): QueueRow {
  return { id } as QueueRow;
}

const LANES: QueuePage["lanes"] = {
  approve: { total: 0, due_soon: 0 },
  coder: { total: 3, due_soon: 0 },
  provider: { total: 0, due_soon: 0 },
  compliance: { total: 0, due_soon: 0 },
};
const PAGE: QueuePage = { items: [row("a"), row("b"), row("c")], lanes: LANES, total: 3, all_total: 3, failed: 0, page_size: 50 };

describe("decision order", () => {
  it("lists the code findings visit code first and keeps only those with a choice to make", () => {
    expect(codeFindings(FINDINGS).map((item) => item.key)).toEqual(["em", "dx:E11.65", "dx:I10"]);
    expect(decisionOrder(FINDINGS, "codes")).toEqual(["em", "dx:E11.65"]);
    expect(questionFindings(FINDINGS).map((item) => item.key)).toEqual(["cdiq-1"]);
    expect(decisionOrder(FINDINGS, "questions")).toEqual(["cdiq-1"]);
    expect(decisionOrder(FINDINGS, "history")).toEqual([]);
  });

  it("moves to the next finding, and from the last one to nothing", () => {
    expect(nextInOrder(["em", "dx:E11.65"], "em")).toBe("dx:E11.65");
    expect(nextInOrder(["em", "dx:E11.65"], "dx:E11.65")).toBeNull();
    expect(nextInOrder(["em", "dx:E11.65"], "gone")).toBe("em");
  });

  it("starts at the first finding, follows the last move and stops after the last finding", () => {
    expect(currentFindingKey(["em", "dx:E11.65"], "codes", null)).toBe("em");
    expect(currentFindingKey(["em", "dx:E11.65"], "codes", { tab: "codes", key: "dx:E11.65" })).toBe("dx:E11.65");
    expect(currentFindingKey(["em", "dx:E11.65"], "codes", { tab: "codes", key: null })).toBeNull();
    expect(currentFindingKey(["cdiq-1"], "questions", { tab: "codes", key: null })).toBe("cdiq-1");
  });
});

describe("choices from the keyboard", () => {
  it("accepts with the suggestion's own choice and rejects with keep or skip", () => {
    expect(choiceFor(EM, true)).toBe("accept");
    expect(choiceFor(EM, false)).toBe("keep");
    expect(choiceFor(ADDED, true)).toBe("add");
    expect(choiceFor(ADDED, false)).toBe("skip");
    expect(choiceFor(QUERY, true)).toBe("ask");
    expect(choiceFor(SUPPORTED, true)).toBeNull();
  });

  it("shows a choice at once without touching the other findings", () => {
    const detail = { findings: FINDINGS } as NoteDetail;
    const changed = withChoice(detail, "em", "keep");
    expect(changed.findings.map((item) => item.choice)).toEqual(["add", "ask", "keep", "keep"]);
    expect(detail.findings[3]?.choice).toBe("accept");
  });
});

describe("review order", () => {
  it("finds the neighbours of a note and the count of its lane", () => {
    expect(neighboursIn(PAGE, "b", "coder")).toEqual({ previous: "a", next: "c", index: 2, total: 3 });
    expect(neighboursIn(PAGE, "x", "coder")).toEqual({ previous: null, next: "a", index: null, total: 3 });
  });

  it("drops an approved note from the order and from its lane count", () => {
    const after = withoutNote(PAGE, "a", "coder");
    expect(after.items.map((item) => item.id)).toEqual(["b", "c"]);
    expect(after.lanes.coder.total).toBe(2);
    expect(neighboursIn(after, "b", "coder")).toEqual({ previous: null, next: "c", index: 1, total: 2 });
    expect(withoutNote(PAGE, "x", "coder")).toBe(PAGE);
  });
});
