import { addDays, addMonths, weekdayOf } from "@/lib/dates";

const DAY_STEPS: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
const MONTH_STEPS: Record<string, number> = { PageUp: -1, PageDown: 1 };
const MONTHS_IN_YEAR = 12;

function offsetInWeek(day: string, weekStartsOn: number): number {
  return ((weekdayOf(day) ?? weekStartsOn) - weekStartsOn + 7) % 7;
}

export function dayForKey(day: string, key: string, shift: boolean, weekStartsOn: number): string | null {
  const days = DAY_STEPS[key];
  if (days !== undefined) return addDays(day, days);
  const months = MONTH_STEPS[key];
  if (months !== undefined) return addMonths(day, shift ? months * MONTHS_IN_YEAR : months);
  if (key === "Home") return addDays(day, -offsetInWeek(day, weekStartsOn));
  if (key === "End") return addDays(day, 6 - offsetInWeek(day, weekStartsOn));
  return null;
}

const FOCUSABLE = "button:not(:disabled):not([tabindex='-1']), input:not(:disabled)";

export function wrapTab(event: { key: string; shiftKey: boolean; preventDefault: () => void }, container: HTMLElement): void {
  if (event.key !== "Tab") return;
  const items = [...container.querySelectorAll<HTMLElement>(FOCUSABLE)];
  const first = items[0];
  const last = items[items.length - 1];
  const target = event.shiftKey ? (document.activeElement === first ? last : null) : document.activeElement === last ? first : null;
  if (!target) return;
  event.preventDefault();
  target.focus();
}
