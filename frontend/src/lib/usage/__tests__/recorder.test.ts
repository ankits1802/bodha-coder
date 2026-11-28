import { describe, expect, it } from "vitest";
import type { UsageEvent } from "@/lib/api/types";
import { HANDOFF_MS, MAX_BATCH, STALL_AFTER_MS, UsageRecorder } from "../recorder";

interface Bench {
  recorder: UsageRecorder;
  advance: (ms: number) => void;
  session: { key: string | null };
}

function bench(): Bench {
  let now = 0;
  let ids = 0;
  const session = { key: "user-1:practice-1" as string | null };
  const recorder = new UsageRecorder({
    clock: () => now,
    newId: () => `event-${(ids += 1)}`,
    sessionKey: () => session.key,
  });
  return { recorder, session, advance: (ms) => (now += ms) };
}

function onlyTask(events: UsageEvent[]) {
  const tasks = events.filter((event) => event.kind === "task");
  expect(tasks).toHaveLength(1);
  return tasks[0];
}

describe("UsageRecorder", () => {
  it("times a note review from open to approval and counts inputs and decisions by how they were made", () => {
    const { recorder, advance } = bench();
    const review = recorder.start("note_review");
    advance(4_000);
    recorder.input("pointer", "findings");
    recorder.input("key", "findings");
    recorder.decided(review, 1);
    advance(2_000);
    recorder.input("pointer", "findings");
    recorder.decided(review, 3);
    recorder.input("scroll", "note");
    advance(6_000);
    recorder.end(review, "completed");

    expect(recorder.take()).toEqual([
      {
        kind: "task",
        event_id: "event-1",
        task: "note_review",
        outcome: "completed",
        duration_ms: 12_000,
        first_decision_ms: 4_000,
        key_inputs: 1,
        pointer_inputs: 2,
        key_decisions: 1,
        pointer_decisions: 3,
      },
    ]);
  });

  it("records a quiet stretch of a minute or more as a stall where the last input was", () => {
    const { recorder, advance } = bench();
    const review = recorder.start("note_review");
    recorder.input("pointer", "claim");
    advance(STALL_AFTER_MS - 1);
    recorder.input("pointer", "findings");
    advance(STALL_AFTER_MS + 5_000);
    recorder.input("key", "claim");
    recorder.end(review, "left");

    const events = recorder.take();
    expect(events.filter((event) => event.kind === "stall")).toEqual([
      { kind: "stall", event_id: "event-2", task: "note_review", step: "findings", duration_ms: STALL_AFTER_MS + 5_000 },
    ]);
    expect(onlyTask(events)).toMatchObject({ outcome: "left", first_decision_ms: null, key_decisions: 0 });
  });

  it("leaves out time with the page hidden and never calls it a stall", () => {
    const { recorder, advance } = bench();
    const upload = recorder.start("upload");
    advance(10_000);
    recorder.hide();
    advance(10 * STALL_AFTER_MS);
    recorder.show();
    advance(5_000);
    recorder.end(upload, "completed");

    const events = recorder.take();
    expect(events.some((event) => event.kind === "stall")).toBe(false);
    expect(onlyTask(events)).toMatchObject({ task: "upload", duration_ms: 15_000 });
  });

  it("drops a task left within a second with no input, and decisions outside a note review", () => {
    const { recorder, advance } = bench();
    const flicker = recorder.start("note_review");
    advance(400);
    recorder.end(flicker, "left");
    const queue = recorder.start("queue");
    advance(3_000);
    recorder.decided(queue, 2);
    recorder.end(queue, "left");

    expect(onlyTask(recorder.take())).toMatchObject({ task: "queue", key_decisions: 0, pointer_decisions: 0, first_decision_ms: null });
  });

  it("counts a queue visit as finished when a note review opens straight after it", () => {
    const { recorder, advance } = bench();
    const first = recorder.start("queue");
    advance(5_000);
    recorder.end(first, "left");
    recorder.start("note_review");
    const second = recorder.start("queue");
    advance(5_000);
    recorder.end(second, "left");
    advance(HANDOFF_MS + 1);
    recorder.start("note_review");

    const queues = recorder.take().filter((event) => event.kind === "task" && event.task === "queue");
    expect(queues.map((event) => event.kind === "task" && event.outcome)).toEqual(["completed", "left"]);
  });

  it("records nothing without a practice session and never sends one session's timings in another", () => {
    const { recorder, advance, session } = bench();
    session.key = null;
    expect(recorder.start("note_review")).toBe(0);
    session.key = "user-1:practice-1";
    const review = recorder.start("note_review");
    advance(5_000);
    recorder.end(review, "left");
    session.key = "user-1:practice-2";

    expect(recorder.take()).toEqual([]);
  });

  it("hands timings over in batches the endpoint accepts", () => {
    const { recorder, advance } = bench();
    for (let index = 0; index < MAX_BATCH + 3; index += 1) {
      const upload = recorder.start("upload");
      advance(2_000);
      recorder.end(upload, "completed");
    }

    expect(recorder.take()).toHaveLength(MAX_BATCH);
    expect(recorder.take()).toHaveLength(3);
    expect(recorder.take()).toEqual([]);
  });
});
