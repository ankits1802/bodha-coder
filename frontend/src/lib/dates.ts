export interface CalendarDate {
  year: number;
  month: number;
  day: number;
}

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

function pad(value: number, width = 2): string {
  return String(value).padStart(width, "0");
}

export function isIsoDate(text: string): boolean {
  const parsed = parseIsoDate(text);
  return parsed !== null && toIsoDate(parsed) === text;
}

export function parseIsoDate(text: string): CalendarDate | null {
  const found = ISO_DATE.exec(text);
  if (!found) return null;
  const [year, month, day] = [Number(found[1]), Number(found[2]), Number(found[3])];
  const probe = new Date(year, month - 1, day);
  if (probe.getFullYear() !== year || probe.getMonth() !== month - 1 || probe.getDate() !== day) return null;
  return { year, month, day };
}

export function toIsoDate(date: CalendarDate): string {
  return `${pad(date.year, 4)}-${pad(date.month)}-${pad(date.day)}`;
}

export function calendarDateOf(moment: Date): CalendarDate {
  return { year: moment.getFullYear(), month: moment.getMonth() + 1, day: moment.getDate() };
}

export function localIsoDate(moment: Date = new Date()): string {
  return toIsoDate(calendarDateOf(moment));
}

export function isoDateInZone(moment: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(moment);
  const value = (type: Intl.DateTimeFormatPartTypes): number => Number(parts.find((part) => part.type === type)?.value);
  return toIsoDate({ year: value("year"), month: value("month"), day: value("day") });
}

export function localDateFromIso(text: string): Date | null {
  const parsed = parseIsoDate(text);
  return parsed ? new Date(parsed.year, parsed.month - 1, parsed.day) : null;
}

export function addDays(text: string, days: number): string | null {
  const local = localDateFromIso(text);
  if (!local) return null;
  local.setDate(local.getDate() + days);
  return localIsoDate(local);
}

export function weekdayOf(text: string): number | null {
  const local = localDateFromIso(text);
  return local ? local.getDay() : null;
}

export function isWeekend(text: string): boolean {
  const weekday = weekdayOf(text);
  return weekday === 0 || weekday === 6;
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

export function dayInMonth(year: number, month: number, day: number): string {
  return toIsoDate({ year, month, day: Math.min(day, daysInMonth(year, month)) });
}

export function addMonths(text: string, months: number): string | null {
  const parsed = parseIsoDate(text);
  if (!parsed) return null;
  const first = new Date(parsed.year, parsed.month - 1 + months, 1);
  return dayInMonth(first.getFullYear(), first.getMonth() + 1, parsed.day);
}

export function clampIsoDate(text: string, min?: string | null, max?: string | null): string {
  if (min && text < min) return min;
  if (max && text > max) return max;
  return text;
}

export function isWithin(text: string, min?: string | null, max?: string | null): boolean {
  return clampIsoDate(text, min, max) === text;
}

export function monthWeeks(year: number, month: number, weekStartsOn: number): (string | null)[][] {
  const lead = (new Date(year, month - 1, 1).getDay() - weekStartsOn + 7) % 7;
  const days = Array.from({ length: daysInMonth(year, month) }, (_, index) => toIsoDate({ year, month, day: index + 1 }));
  const cells: (string | null)[] = [...Array<null>(lead).fill(null), ...days];
  const weeks: (string | null)[][] = [];
  for (let start = 0; start < cells.length; start += 7) {
    const week = cells.slice(start, start + 7);
    weeks.push([...week, ...Array<null>(7 - week.length).fill(null)]);
  }
  return weeks;
}
