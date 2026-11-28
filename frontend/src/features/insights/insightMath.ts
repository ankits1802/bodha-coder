import type { InsightDays, Insights, Outcomes } from "@/lib/api/types";
import { addDays, isWeekend } from "@/lib/dates";

export const DEFAULT_DAYS: InsightDays = 14;
const AXIS_SEGMENTS = 3;
const NICE_STEPS = [1, 2, 5, 10];

export function rangeStart(today: string, days: InsightDays): string {
  return addDays(today, -(days - 1)) ?? today;
}

export interface DayBar {
  date: string;
  notes: number;
  weekend: boolean;
}

export function dailyBars(perDay: Insights["per_day"], start: string, today: string): DayBar[] {
  const counts = new Map(perDay.map((entry) => [entry.date, entry.notes]));
  const dates = new Set<string>(perDay.map((entry) => entry.date));
  for (let day: string | null = start; day !== null && day <= today; day = addDays(day, 1)) dates.add(day);
  return [...dates].sort().map((date) => ({ date, notes: counts.get(date) ?? 0, weekend: isWeekend(date) }));
}

export function axisMax(values: number[]): number {
  const highest = Math.max(0, ...values);
  if (highest === 0) return AXIS_SEGMENTS;
  const raw = highest / AXIS_SEGMENTS;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = (NICE_STEPS.find((nice) => nice * magnitude >= raw) ?? 10) * magnitude;
  return step * AXIS_SEGMENTS;
}

export function axisTicks(max: number): number[] {
  return Array.from({ length: AXIS_SEGMENTS + 1 }, (_, index) => (max / AXIS_SEGMENTS) * (AXIS_SEGMENTS - index));
}

export type OutcomeKey = keyof Outcomes;
export const OUTCOME_ORDER: readonly OutcomeKey[] = ["matched", "billed_too_low", "diagnosis_changes", "billed_too_high"];

export function outcomeTotal(outcomes: Outcomes): number {
  return OUTCOME_ORDER.reduce((sum, key) => sum + outcomes[key], 0);
}

export function notesRead(insights: Insights): number {
  return insights.per_day.reduce((sum, entry) => sum + entry.notes, 0);
}

export function isQuiet(insights: Insights): boolean {
  return notesRead(insights) === 0 && insights.approved === 0 && insights.providers.length === 0 && outcomeTotal(insights.outcomes) === 0;
}
