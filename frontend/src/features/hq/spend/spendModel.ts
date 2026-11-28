import type { HqExpenditure, SpendRange } from "@/lib/api/types";
import { daysInMonth, isIsoDate, toIsoDate, type CalendarDate } from "@/lib/dates";
import { toCsv } from "@/lib/download";
import { HQ_TEXT } from "../strings";

export const SPEND_PRESETS = ["thisMonth", "lastMonth", "last30Days", "thisYear"] as const;
export type SpendPreset = (typeof SPEND_PRESETS)[number];

const DEFAULT_PRESET: SpendPreset = "thisMonth";
const SPEND_PATH = "/hq/spend";
const TRAILING_DAYS = 30;
const COST_PLACES = 2;
const UNIT_COST_PLACES = 4;

export function utcToday(now: Date = new Date()): CalendarDate {
  return { year: now.getUTCFullYear(), month: now.getUTCMonth() + 1, day: now.getUTCDate() };
}

function daysBefore(day: CalendarDate, days: number): string {
  const moment = new Date(Date.UTC(day.year, day.month - 1, day.day - days));
  return toIsoDate(utcToday(moment));
}

function previousMonth(today: CalendarDate): SpendRange {
  const year = today.month === 1 ? today.year - 1 : today.year;
  const month = today.month === 1 ? 12 : today.month - 1;
  return { from: toIsoDate({ year, month, day: 1 }), to: toIsoDate({ year, month, day: daysInMonth(year, month) }) };
}

const PRESET_RANGES: Record<SpendPreset, (today: CalendarDate) => SpendRange> = {
  thisMonth: (today) => ({ from: toIsoDate({ ...today, day: 1 }), to: toIsoDate(today) }),
  lastMonth: previousMonth,
  last30Days: (today) => ({ from: daysBefore(today, TRAILING_DAYS - 1), to: toIsoDate(today) }),
  thisYear: (today) => ({ from: toIsoDate({ year: today.year, month: 1, day: 1 }), to: toIsoDate(today) }),
};

export function presetRange(preset: SpendPreset, today: CalendarDate): SpendRange {
  return PRESET_RANGES[preset](today);
}

export function presetOf(range: SpendRange, today: CalendarDate): SpendPreset | null {
  const matches = (preset: SpendPreset): boolean => {
    const candidate = presetRange(preset, today);
    return candidate.from === range.from && candidate.to === range.to;
  };
  return SPEND_PRESETS.find(matches) ?? null;
}

export function rangeFrom(from: string | null, to: string | null, today: CalendarDate): SpendRange {
  if (from && to && isIsoDate(from) && isIsoDate(to) && from <= to) return { from, to };
  return presetRange(DEFAULT_PRESET, today);
}

export function spendPath(range: SpendRange): string {
  return `${SPEND_PATH}?${new URLSearchParams({ from: range.from, to: range.to }).toString()}`;
}

export function providerCount(report: HqExpenditure): number {
  return report.practices.reduce((count, practice) => count + practice.providers.length, 0);
}

export function spendCsv(report: HqExpenditure): string {
  const rows = report.practices.flatMap((practice) =>
    practice.providers.map((provider) => [
      practice.name,
      provider.name,
      provider.analyses,
      provider.notes,
      provider.input_tokens,
      provider.output_tokens,
      provider.cost_usd.toFixed(COST_PLACES),
      provider.cost_per_note_usd === null ? null : provider.cost_per_note_usd.toFixed(UNIT_COST_PLACES),
      provider.unpriced_analyses,
    ]),
  );
  return toCsv([...HQ_TEXT.spend.csvHeader], rows);
}

export function spendFileName(range: SpendRange): string {
  return HQ_TEXT.spend.fileName(range.from.replaceAll("-", ""), range.to.replaceAll("-", ""));
}
