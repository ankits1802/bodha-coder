import { ApiError } from "@/lib/api/errors";
import type { UsageEvent, UsageStep } from "@/lib/api/types";
import { TASK_STEPS, type InputKind, type UsageRecorder } from "./recorder";

export const FLUSH_EVERY_MS = 30_000;
export const STEP_ATTRIBUTE = "data-usage-step";

const KNOWN_STEPS: ReadonlySet<string> = new Set(Object.values(TASK_STEPS).flat());
const INPUTS: readonly [string, InputKind][] = [
  ["keydown", "key"],
  ["pointerdown", "pointer"],
  ["wheel", "scroll"],
  ["scroll", "scroll"],
  ["touchmove", "scroll"],
];
const SERVER_ERROR = 500;

export type UsageSender = (events: UsageEvent[], keepalive: boolean) => Promise<void>;

export interface CaptureTargets {
  window: Pick<Window, "addEventListener" | "removeEventListener" | "setInterval" | "clearInterval">;
  document: Pick<Document, "addEventListener" | "removeEventListener" | "visibilityState">;
}

export function stepOf(target: EventTarget | null): UsageStep | null {
  if (!(target instanceof Element)) return null;
  const step = target.closest(`[${STEP_ATTRIBUTE}]`)?.getAttribute(STEP_ATTRIBUTE) ?? null;
  return step !== null && KNOWN_STEPS.has(step) ? (step as UsageStep) : null;
}

function worthRetrying(error: unknown): boolean {
  return !(error instanceof ApiError) || error.status >= SERVER_ERROR;
}

export function flushUsage(recorder: UsageRecorder, send: UsageSender, keepalive: boolean): void {
  for (let batch = recorder.take(); batch.length > 0; batch = recorder.take()) {
    const sent = batch;
    void send(sent, keepalive).catch((error: unknown) => {
      if (worthRetrying(error)) recorder.requeue(sent);
    });
  }
}

export function startUsageCapture(recorder: UsageRecorder, send: UsageSender, targets: CaptureTargets): () => void {
  const listeners = INPUTS.map(([name, kind]) => [name, (event: Event) => recorder.input(kind, stepOf(event.target))] as const);
  const leave = (): void => {
    recorder.hide();
    flushUsage(recorder, send, true);
  };
  const visibility = (): void => {
    if (targets.document.visibilityState === "hidden") leave();
    else recorder.show();
  };
  for (const [name, listener] of listeners) targets.window.addEventListener(name, listener, { capture: true, passive: true });
  targets.window.addEventListener("pagehide", leave);
  targets.document.addEventListener("visibilitychange", visibility);
  const timer = targets.window.setInterval(() => flushUsage(recorder, send, false), FLUSH_EVERY_MS);
  return () => {
    for (const [name, listener] of listeners) targets.window.removeEventListener(name, listener, { capture: true });
    targets.window.removeEventListener("pagehide", leave);
    targets.document.removeEventListener("visibilitychange", visibility);
    targets.window.clearInterval(timer);
    flushUsage(recorder, send, true);
  };
}
