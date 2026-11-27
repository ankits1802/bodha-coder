import { dayInMonth, parseIsoDate, toIsoDate, type CalendarDate } from "@/lib/dates";
import { MONTH_NAMES } from "@/lib/format";
import type { SelectOption } from "../select/selectModel";

export const YEARS_BEFORE = 100;
export const YEARS_AFTER = 10;

export function viewOf(day: string): CalendarDate {
  const parts = parseIsoDate(day);
  if (!parts) throw new Error(`not an ISO calendar date: ${day}`);
  return parts;
}

function monthTouches(year: number, month: number, min?: string, max?: string): boolean {
  return (!max || toIsoDate({ year, month, day: 1 }) <= max) && (!min || dayInMonth(year, month, 31) >= min);
}

export function canShowEarlier(year: number, month: number, min?: string): boolean {
  return !min || toIsoDate({ year, month, day: 1 }) > min;
}

export function canShowLater(year: number, month: number, max?: string): boolean {
  return !max || dayInMonth(year, month, 31) < max;
}

export function monthOptions(year: number, min?: string, max?: string): SelectOption[] {
  return MONTH_NAMES.map((name, index) => ({
    value: String(index + 1),
    label: name,
    disabled: !monthTouches(year, index + 1, min, max),
  }));
}

export function yearOptions(shown: number, today: string, min?: string, max?: string): SelectOption[] {
  const thisYear = viewOf(today).year;
  const first = Math.min(min ? viewOf(min).year : thisYear - YEARS_BEFORE, shown);
  const last = Math.max(max ? viewOf(max).year : thisYear + YEARS_AFTER, shown);
  return Array.from({ length: last - first + 1 }, (_, index) => ({ value: String(first + index), label: String(first + index) }));
}
