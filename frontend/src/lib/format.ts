import { localDateFromIso } from "./dates";

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
const moneyChangeFormat = new Intl.NumberFormat(MONEY_LOCALE, {
  style: "currency",
  currency: MEDICARE_CURRENCY,
  signDisplay: "exceptZero",
});
const shortDay = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short" });
const longDay = new Intl.DateTimeFormat(LOCALE, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
const fullDay = new Intl.DateTimeFormat(LOCALE, { weekday: "long", day: "numeric", month: "long" });
const dayWithYear = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric" });
const timeOfDay = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit", hour12: false });

export type DayStyle = "short" | "long" | "full" | "year";

const DAY_FORMATS: Record<DayStyle, Intl.DateTimeFormat> = {
  short: shortDay,
  long: longDay,
  full: fullDay,
  year: dayWithYear,
};

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

export function formatMoneyChange(value: number | null): string {
  return value === null ? FORMAT_WORDS.empty : moneyChangeFormat.format(value);
}

export function formatMinutes(minutes: number | null): string {
  if (minutes === null) return FORMAT_WORDS.empty;
  if (minutes < 60) return `${tenthsFormat.format(minutes)} min`;
  if (minutes < 24 * 60) return `${tenthsFormat.format(minutes / 60)} h`;
  return `${tenthsFormat.format(minutes / (24 * 60))} d`;
}

export function formatCalendarDay(isoDate: string, style: DayStyle = "short"): string {
  const local = localDateFromIso(isoDate);
  return local ? DAY_FORMATS[style].format(local).replace(",", "") : isoDate;
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
