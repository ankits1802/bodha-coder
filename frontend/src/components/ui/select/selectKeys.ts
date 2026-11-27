import type { KeyboardEvent } from "react";
import { PAGE_STEP, edgeOption, stepOption, type SelectOption } from "./selectModel";

export const TYPEAHEAD_MS = 500;

export function isPrintable(event: KeyboardEvent): boolean {
  return event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey;
}

const STEPS: Record<string, number> = { ArrowDown: 1, ArrowUp: -1, PageDown: PAGE_STEP, PageUp: -PAGE_STEP };

export function navigatedOption(options: readonly SelectOption[], shown: readonly number[], active: number, key: string): number | null {
  if (key === "Home") return edgeOption(options, shown, "first");
  if (key === "End") return edgeOption(options, shown, "last");
  const step = STEPS[key];
  return step === undefined ? null : stepOption(options, shown, active, step);
}

export function opensList(event: KeyboardEvent): boolean {
  return ["Enter", " ", "ArrowDown", "ArrowUp", "Home", "End"].includes(event.key);
}
