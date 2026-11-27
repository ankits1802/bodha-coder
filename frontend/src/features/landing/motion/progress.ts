export type ProgressMode = "enter" | "pin";

const ENTER_START = 0.8;
const ENTER_END = 0.15;

function clamp(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function enterProgress(top: number, viewport: number): number {
  const start = viewport * ENTER_START;
  const end = viewport * ENTER_END;
  return clamp((start - top) / (start - end));
}

export function pinProgress(top: number, height: number, viewport: number): number {
  const travel = height - viewport;
  if (travel <= 0) return top <= 0 ? 1 : 0;
  return clamp(-top / travel);
}

export function actFor(progress: number, acts: number): number {
  return Math.min(acts - 1, Math.floor(progress * acts));
}

function matches(query: string): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

export function prefersReducedMotion(): boolean {
  return matches("(prefers-reduced-motion: reduce)");
}

export function hasFinePointer(): boolean {
  return matches("(pointer: fine)");
}
