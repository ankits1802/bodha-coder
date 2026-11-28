import type { UsageEvent, UsageOutcome, UsageStep, UsageTask, UsageTaskEvent } from "@/lib/api/types";

export const STALL_AFTER_MS = 60_000;
export const MIN_TASK_MS = 1_000;
export const MAX_DURATION_MS = 4 * 60 * 60 * 1000;
export const MAX_COUNT = 100_000;
export const MAX_BATCH = 50;
export const MAX_PENDING = 500;
export const HANDOFF_MS = 2_000;

export const TASK_STEPS: Record<UsageTask, readonly UsageStep[]> = {
  note_review: ["summary", "note", "findings", "claim", "dialog", "history", "navigation"],
  queue: ["queue"],
  upload: ["upload"],
  billing_export: ["billing"],
};

const FIRST_STEP: Record<UsageTask, UsageStep> = { note_review: "note", queue: "queue", upload: "upload", billing_export: "billing" };
const COMPLETED_BY: Partial<Record<UsageTask, UsageTask>> = { queue: "note_review" };
const DECIDING: readonly UsageTask[] = ["note_review"];

export type InputKind = "key" | "pointer" | "scroll";

export interface RecorderDeps {
  clock: () => number;
  newId: () => string;
  sessionKey: () => string | null;
}

interface OpenTask {
  id: string;
  task: UsageTask;
  session: string;
  shownMs: number;
  shownSince: number | null;
  lastInputAt: number;
  step: UsageStep;
  lastKind: "key" | "pointer" | null;
  keys: number;
  pointers: number;
  keyDecisions: number;
  pointerDecisions: number;
  firstDecisionMs: number | null;
}

interface Pending {
  session: string;
  event: UsageEvent;
}

interface Handoff {
  id: string;
  task: UsageTask;
  at: number;
}

const capped = (value: number, limit: number): number => Math.min(Math.max(0, Math.round(value)), limit);

export class UsageRecorder {
  private readonly open = new Map<number, OpenTask>();
  private pending: Pending[] = [];
  private handoffs: Handoff[] = [];
  private lastHandle = 0;
  private shown = true;

  constructor(private readonly deps: RecorderDeps) {}

  start(task: UsageTask): number {
    const session = this.deps.sessionKey();
    if (session === null) return 0;
    const now = this.deps.clock();
    this.completeHandoffs(task, now);
    this.lastHandle += 1;
    this.open.set(this.lastHandle, {
      id: this.deps.newId(),
      task,
      session,
      shownMs: 0,
      shownSince: this.shown ? now : null,
      lastInputAt: now,
      step: FIRST_STEP[task],
      lastKind: null,
      keys: 0,
      pointers: 0,
      keyDecisions: 0,
      pointerDecisions: 0,
      firstDecisionMs: null,
    });
    return this.lastHandle;
  }

  end(handle: number, outcome: UsageOutcome): void {
    const open = this.open.get(handle);
    if (!open) return;
    this.open.delete(handle);
    const now = this.deps.clock();
    this.noteStall(open, now);
    const duration = this.elapsed(open, now);
    if (duration < MIN_TASK_MS && open.keys + open.pointers === 0) return;
    this.push(open.session, this.taskEvent(open, outcome, duration));
    if (outcome === "left" && COMPLETED_BY[open.task]) this.handoffs.push({ id: open.id, task: open.task, at: now });
  }

  decided(handle: number, count: number): void {
    const open = this.open.get(handle);
    if (!open || count <= 0 || !DECIDING.includes(open.task)) return;
    open.firstDecisionMs ??= this.elapsed(open, this.deps.clock());
    if (open.lastKind === "key") open.keyDecisions += count;
    else open.pointerDecisions += count;
  }

  input(kind: InputKind, step: UsageStep | null): void {
    if (!this.shown) return;
    const now = this.deps.clock();
    for (const open of this.open.values()) {
      this.noteStall(open, now);
      open.lastInputAt = now;
      if (step && TASK_STEPS[open.task].includes(step)) open.step = step;
      if (kind === "key") open.keys += 1;
      if (kind === "pointer") open.pointers += 1;
      if (kind !== "scroll") open.lastKind = kind;
    }
  }

  hide(): void {
    if (!this.shown) return;
    const now = this.deps.clock();
    for (const open of this.open.values()) {
      this.noteStall(open, now);
      open.shownMs = this.elapsed(open, now);
      open.shownSince = null;
    }
    this.shown = false;
  }

  show(): void {
    if (this.shown) return;
    const now = this.deps.clock();
    for (const open of this.open.values()) {
      open.shownSince = now;
      open.lastInputAt = now;
    }
    this.shown = true;
  }

  take(): UsageEvent[] {
    const session = this.deps.sessionKey();
    const mine = this.pending.filter((item) => item.session === session);
    const batch = mine.slice(0, MAX_BATCH);
    this.pending = mine.slice(MAX_BATCH);
    return batch.map((item) => item.event);
  }

  requeue(events: UsageEvent[]): void {
    const session = this.deps.sessionKey();
    if (session === null) return;
    this.pending = [...events.map((event) => ({ session, event })), ...this.pending].slice(-MAX_PENDING);
  }

  private elapsed(open: OpenTask, now: number): number {
    return open.shownMs + (open.shownSince === null ? 0 : now - open.shownSince);
  }

  private noteStall(open: OpenTask, now: number): void {
    const quiet = now - open.lastInputAt;
    if (open.shownSince === null || quiet < STALL_AFTER_MS) return;
    const event = { kind: "stall", event_id: this.deps.newId(), task: open.task, step: open.step, duration_ms: capped(quiet, MAX_DURATION_MS) } as const;
    this.push(open.session, event);
    open.lastInputAt = now;
  }

  private taskEvent(open: OpenTask, outcome: UsageOutcome, duration: number): UsageTaskEvent {
    const duration_ms = capped(duration, MAX_DURATION_MS);
    return {
      kind: "task",
      event_id: open.id,
      task: open.task,
      outcome,
      duration_ms,
      first_decision_ms: open.firstDecisionMs === null ? null : Math.min(capped(open.firstDecisionMs, MAX_DURATION_MS), duration_ms),
      key_inputs: capped(open.keys, MAX_COUNT),
      pointer_inputs: capped(open.pointers, MAX_COUNT),
      key_decisions: capped(open.keyDecisions, MAX_COUNT),
      pointer_decisions: capped(open.pointerDecisions, MAX_COUNT),
    };
  }

  private completeHandoffs(task: UsageTask, now: number): void {
    const due = this.handoffs.filter((handoff) => COMPLETED_BY[handoff.task] === task && now - handoff.at <= HANDOFF_MS);
    this.handoffs = [];
    for (const handoff of due) {
      const item = this.pending.find((entry) => entry.event.event_id === handoff.id && entry.event.kind === "task");
      if (item && item.event.kind === "task") item.event = { ...item.event, outcome: "completed" };
    }
  }

  private push(session: string, event: UsageEvent): void {
    this.pending = [...this.pending, { session, event }].slice(-MAX_PENDING);
  }
}
