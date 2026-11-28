import { isIsoDate, localDateFromIso, toIsoDate, type CalendarDate } from "./dates";

const LOCALE = "en-GB";
const MONEY_LOCALE = "en-US";
const MEDICARE_CURRENCY = "USD";
const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export const FORMAT_WORDS = {
  overdue: "Overdue",
  now: "Now",
  yesterday: "Yesterday",
  empty: "—",
} as const;

const numberFormat = new Intl.NumberFormat(LOCALE);
const percentFormat = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 1 });
const tenthsFormat = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 });
const moneyFormat = new Intl.NumberFormat(MONEY_LOCALE, { style: "currency", currency: MEDICARE_CURRENCY });
const unitCostFormat = new Intl.NumberFormat(MONEY_LOCALE, {
  style: "currency",
  currency: MEDICARE_CURRENCY,
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});
const wholeDollarFormat = new Intl.NumberFormat(MONEY_LOCALE, {
  style: "currency",
  currency: MEDICARE_CURRENCY,
  maximumFractionDigits: 0,
});
const moneyChangeFormat = new Intl.NumberFormat(MONEY_LOCALE, {
  style: "currency",
  currency: MEDICARE_CURRENCY,
  signDisplay: "exceptZero",
});
const shortDay = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short" });
const longDay = new Intl.DateTimeFormat(LOCALE, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
const fullDay = new Intl.DateTimeFormat(LOCALE, { weekday: "long", day: "numeric", month: "long" });
const dayWithYear = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric" });
const completeDay = new Intl.DateTimeFormat(LOCALE, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
const timeOfDay = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit", hour12: false });
const monthOfYear = new Intl.DateTimeFormat(LOCALE, { month: "long", year: "numeric" });
const monthName = new Intl.DateTimeFormat(LOCALE, { month: "long" });
const weekdayNarrow = new Intl.DateTimeFormat(LOCALE, { weekday: "narrow" });
const weekdayLong = new Intl.DateTimeFormat(LOCALE, { weekday: "long" });

export type DayStyle = "short" | "long" | "full" | "year" | "complete";

const DAY_FORMATS: Record<DayStyle, Intl.DateTimeFormat> = {
  short: shortDay,
  long: longDay,
  full: fullDay,
  year: dayWithYear,
  complete: completeDay,
};

export const WEEK_STARTS_ON = 1;

const REFERENCE_YEAR = 2000;
const REFERENCE_SUNDAY = { year: 2023, monthIndex: 11, day: 31 } as const;

export const MONTH_NAMES: readonly string[] = Array.from({ length: 12 }, (_, index) => monthName.format(new Date(REFERENCE_YEAR, index, 1)));

export interface WeekdayName {
  narrow: string;
  long: string;
}

export const WEEKDAY_NAMES: readonly WeekdayName[] = Array.from({ length: 7 }, (_, index) => {
  const day = new Date(REFERENCE_SUNDAY.year, REFERENCE_SUNDAY.monthIndex, REFERENCE_SUNDAY.day + ((WEEK_STARTS_ON + index) % 7));
  return { narrow: weekdayNarrow.format(day), long: weekdayLong.format(day) };
});

const ISO_LIKE_DAY = /^(\d{4})-(\d{1,2})-(\d{1,2})$/;
const NUMERIC_DAY = /^(\d{1,2})[./\-\s](\d{1,2})[./\-\s](\d{4})$/;
const NAMED_DAY = /^(?:[a-z]+,?\s+)?(\d{1,2})\s+([a-z]+)\.?,?\s+(\d{4})$/i;
const MIN_MONTH_PREFIX = 3;

const HQ_WORD = /(?<![\w@./-])hq(?![\w@./-])/gi;

export function sentenceCase(text: string): string {
  const named = text.replace(HQ_WORD, "HQ");
  return named.charAt(0).toUpperCase() + named.slice(1);
}

export function formatCount(value: number): string {
  return numberFormat.format(value);
}

export function ratio(part: number, whole: number): number | null {
  return whole > 0 ? part / whole : null;
}

export function formatPercent(value: number | null): string {
  return value === null ? FORMAT_WORDS.empty : percentFormat.format(value);
}

export function formatMoney(value: number | null): string {
  return value === null ? FORMAT_WORDS.empty : moneyFormat.format(value);
}

export function formatUnitCost(value: number | null): string {
  return value === null ? FORMAT_WORDS.empty : unitCostFormat.format(value);
}

export function formatWholeDollars(cents: number): string {
  return wholeDollarFormat.format(Math.round(cents / 100));
}

export function formatMoneyChange(value: number | null): string {
  return value === null ? FORMAT_WORDS.empty : moneyChangeFormat.format(value);
}

export function formatMinutes(minutes: number | null): string {
  if (minutes === null) return FORMAT_WORDS.empty;
  if (minutes < 60) return `${tenthsFormat.format(minutes)} min`;
  if (minutes < 24 * 60) return `${tenthsFormat.format(minutes / 60)} h`;
  return `${tenthsFormat.format(minutes / (24 * 60))} d`;
}

export function formatSeconds(seconds: number | null): string {
  if (seconds === null) return FORMAT_WORDS.empty;
  if (seconds < 60) return `${tenthsFormat.format(seconds)} s`;
  return formatMinutes(seconds / 60);
}

export function formatCalendarDay(isoDate: string | null, style: DayStyle = "short"): string {
  if (isoDate === null) return FORMAT_WORDS.empty;
  const local = localDateFromIso(isoDate);
  return local ? DAY_FORMATS[style].format(local).replace(",", "") : isoDate;
}

function monthFromName(word: string): number | null {
  const lower = word.toLocaleLowerCase(LOCALE);
  if (lower.length < MIN_MONTH_PREFIX) return null;
  const index = MONTH_NAMES.findIndex((name) => name.toLocaleLowerCase(LOCALE).startsWith(lower));
  return index === -1 ? null : index + 1;
}

function typedDayParts(text: string): CalendarDate | null {
  const iso = ISO_LIKE_DAY.exec(text);
  if (iso) return { year: Number(iso[1]), month: Number(iso[2]), day: Number(iso[3]) };
  const numeric = NUMERIC_DAY.exec(text);
  if (numeric) return { day: Number(numeric[1]), month: Number(numeric[2]), year: Number(numeric[3]) };
  const named = NAMED_DAY.exec(text);
  const month = named ? monthFromName(named[2] ?? "") : null;
  return named && month ? { day: Number(named[1]), month, year: Number(named[3]) } : null;
}

export function parseCalendarDay(text: string): string | null {
  const parts = typedDayParts(text.trim());
  if (!parts) return null;
  const iso = toIsoDate(parts);
  return isIsoDate(iso) ? iso : null;
}

export function formatMonthYear(year: number, month: number): string {
  return monthOfYear.format(new Date(year, month - 1, 1));
}

export function formatDay(moment: Date, style: DayStyle = "short"): string {
  return DAY_FORMATS[style].format(moment);
}

export function formatTime(instant: string | Date): string {
  return timeOfDay.format(typeof instant === "string" ? new Date(instant) : instant);
}

export function formatInstantDay(instant: string): string {
  return shortDay.format(new Date(instant));
}

export function formatDateTime(instant: string): string {
  const moment = new Date(instant);
  return `${shortDay.format(moment)}, ${timeOfDay.format(moment)}`;
}

export interface DueIn {
  text: string;
  overdue: boolean;
}

export function formatDueIn(instant: string, now: Date = new Date()): DueIn {
  const left = new Date(instant).getTime() - now.getTime();
  if (left <= 0) return { text: FORMAT_WORDS.overdue, overdue: true };
  if (left < HOUR) return { text: `${Math.max(1, Math.round(left / MINUTE))} min`, overdue: false };
  if (left < DAY) return { text: `${Math.round(left / HOUR)} h`, overdue: false };
  return { text: `${Math.round(left / DAY)} d`, overdue: false };
}

export function formatSince(instant: string, now: Date = new Date()): string {
  const moment = new Date(instant);
  const passed = now.getTime() - moment.getTime();
  if (passed < 2 * MINUTE) return FORMAT_WORDS.now;
  if (passed < HOUR) return `${Math.round(passed / MINUTE)} min ago`;
  if (passed < DAY && moment.getDate() === now.getDate()) return `${Math.round(passed / HOUR)} h ago`;
  if (passed < 2 * DAY) return FORMAT_WORDS.yesterday;
  return shortDay.format(moment);
}

export function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
