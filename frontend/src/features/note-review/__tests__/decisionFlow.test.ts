import { describe, expect, it } from "vitest";
import type { QueuePage, QueueRow } from "@/lib/api/types";
import { choiceFor, nextInOrder, shownChoice, stepInOrder, withChoice } from "../decisionFlow";
import { currentFindingKey } from "../useFindingFocus";
import { neighboursIn, withoutNote, type ReviewScope } from "../useNoteData";
import { finding, noteDetail, queueTotals } from "./fixtures";

const EM = finding({ kind: "em", key: "em", action: "lower", code_before: "99215", code_after: "99214", choice: "accept", allowed: ["accept", "keep"] });
const SUPPORTED = finding({});
const ADDED = finding({ key: "dx:E11.65", action: "add", code_before: null, code_after: "E11.65", choice: "add", allowed: ["add", "skip"] });
const QUERY = finding({ kind: "cdi_query", key: "cdiq-1", action: "ask", code_before: null, choice: "ask", allowed: ["ask", "skip"] });
const FINDINGS = [ADDED, QUERY, SUPPORTED, EM];

function row(id: string): QueueRow {
  return { id } as QueueRow;
}

const CODER: ReviewScope = { lane: "coder", reason: null };
const QUESTIONS: ReviewScope = { lane: "provider", reason: "questions" };
const PAGE: QueuePage = {
  items: [row("a"), row("b"), row("c")],
  ...queueTotals({ coder: 3, provider: 2 }, { questions: 2 }),
  total: 3,
  all_total: 3,
  failed: 0,
  page_size: 50,
};

describe("moving between findings", () => {
  it("moves to the next finding, and from the last one to nothing", () => {
    expect(nextInOrder(["em", "dx:E11.65"], "em")).toBe("dx:E11.65");
    expect(nextInOrder(["em", "dx:E11.65"], "dx:E11.65")).toBeNull();
    expect(nextInOrder(["em", "dx:E11.65"], "gone")).toBe("em");
  });

  it("steps down past the last finding to Approve and back up from Approve to the last finding", () => {
    const order = ["em", "dx:E11.65", "cdiq-1"];
    expect(stepInOrder(order, "em", 1)).toBe("dx:E11.65");
    expect(stepInOrder(order, "cdiq-1", 1)).toBeNull();
    expect(stepInOrder(order, null, 1)).toBeNull();
    expect(stepInOrder(order, null, -1)).toBe("cdiq-1");
    expect(stepInOrder(order, "em", -1)).toBe("em");
    expect(stepInOrder(order, "gone", -1)).toBe("em");
  });

  it("starts at the first finding, follows the last move and stops after the last finding", () => {
    expect(currentFindingKey(["em", "dx:E11.65"], null)).toBe("em");
    expect(currentFindingKey(["em", "dx:E11.65"], { key: "dx:E11.65" })).toBe("dx:E11.65");
    expect(currentFindingKey(["em", "dx:E11.65"], { key: null })).toBeNull();
    expect(currentFindingKey(["cdiq-1"], { key: "em" })).toBe("cdiq-1");
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
    const detail = noteDetail(FINDINGS);
    const changed = withChoice(detail, "em", "keep");
    expect(changed.findings.map((item) => item.choice)).toEqual(["add", "ask", "keep", "keep"]);
    expect(changed.findings[3]?.decided).toBe(true);
    expect(detail.findings[3]?.choice).toBe("accept");
  });

  it("shows no choice on a finding compliance sent back until it is decided again", () => {
    const returned = finding({ ...EM, decide_again: true });
    expect(shownChoice(returned)).toBeNull();
    const decided = withChoice(noteDetail([returned]), "em", "accept").findings[0];
    expect(decided && shownChoice(decided)).toBe("accept");
  });
});

describe("review order", () => {
  it("finds the neighbours of a note and the count of its lane", () => {
    expect(neighboursIn(PAGE, "b", CODER)).toEqual({ previous: "a", next: "c", index: 2, total: 3 });
    expect(neighboursIn(PAGE, "x", CODER)).toEqual({ previous: null, next: "a", index: null, total: 3 });
  });

  it("drops an approved note from the order and from its lane count", () => {
    const after = withoutNote(PAGE, "a", CODER);
    expect(after.items.map((item) => item.id)).toEqual(["b", "c"]);
    expect(after.lanes.coder.total).toBe(2);
    expect(neighboursIn(after, "b", CODER)).toEqual({ previous: null, next: "c", index: 1, total: 2 });
    expect(withoutNote(PAGE, "x", CODER)).toBe(PAGE);
  });

  it("keeps a split of the provider lane to itself and counts it down", () => {
    const after = withoutNote(PAGE, "a", QUESTIONS);
    expect(after.provider_reasons.questions.total).toBe(1);
    expect(after.lanes.provider.total).toBe(1);
    expect(after.provider_reasons.waiting_on_provider.total).toBe(0);
  });
});
