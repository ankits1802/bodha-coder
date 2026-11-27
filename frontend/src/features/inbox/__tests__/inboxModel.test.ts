import { describe, expect, it } from "vitest";
import type { InboxEntry } from "@/lib/api/types";
import { inboxMeta, inboxSentence, inboxTarget } from "../inboxModel";
import { inboxEntry } from "./inboxFixtures";

function sentence(change: Partial<InboxEntry>): string {
  return inboxSentence(inboxEntry(change));
}

describe("inbox sentences", () => {
  it("says what happened for each kind, with who did it", () => {
    expect(sentence({ kind: "provider_answered", payload: { questions: 3 } })).toBe("Elena Varga answered 3 questions");
    expect(sentence({ kind: "provider_answered", payload: { questions: 1 } })).toBe("Elena Varga answered 1 question");
    expect(sentence({ kind: "level_disagreed" })).toBe("Elena Varga disagreed with a visit level you approved");
    expect(sentence({ kind: "request_expired", actor_name: "Bodha", payload: { purpose: "questions" } })).toBe("A provider request expired");
    expect(sentence({ kind: "request_expired", actor_name: "Bodha", payload: { purpose: "level_change" } })).toBe("A visit level request expired");
    expect(sentence({ kind: "mentioned", actor_name: "Priya Nair", payload: { comment_id: "c-1", on: "note" } })).toBe("Priya Nair mentioned you");
    expect(sentence({ kind: "training_assigned", actor_name: "Ana Ruiz", payload: { run_id: "run-1", notes: 4 } })).toBe(
      "Ana Ruiz assigned you 4 training notes",
    );
    expect(sentence({ kind: "payment_failed", actor_name: "Bodha", payload: { access_until: "2026-12-08" } })).toBe(
      "Payment failed. Access continues until 8 Dec 2026",
    );
    expect(sentence({ kind: "plan_ending", actor_name: "Bodha", payload: { ends_on: "2026-12-01" } })).toBe("The plan ends on 1 Dec 2026");
    expect(sentence({ kind: "compliance_returned", actor_name: "Ruth Cole", payload: {} })).toBe("Ruth Cole returned a note");
  });

  it("names the patient and the visit day only when the note is known", () => {
    expect(inboxMeta(inboxEntry({}))).toBe("Marisol Reyes · 25 Nov");
    expect(inboxMeta(inboxEntry({ patient_name: null, service_date: null }))).toBeNull();
  });
});

describe("inbox targets", () => {
  it("opens the note, its history for a mention, training or the plan", () => {
    expect(inboxTarget(inboxEntry({ kind: "provider_answered" }))).toBe("/notes/note-1");
    expect(inboxTarget(inboxEntry({ kind: "mentioned" }))).toBe("/notes/note-1?tab=history");
    expect(inboxTarget(inboxEntry({ kind: "training_assigned", note_id: null }))).toBe("/training");
    expect(inboxTarget(inboxEntry({ kind: "payment_failed", note_id: null }))).toBe("/plan");
    expect(inboxTarget(inboxEntry({ kind: "plan_ending", note_id: null }))).toBe("/plan");
    expect(inboxTarget(inboxEntry({ kind: "level_disagreed", note_id: null }))).toBeNull();
  });
});
