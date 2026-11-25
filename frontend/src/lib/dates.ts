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

export function isWeekend(text: string): boolean {
  const local = localDateFromIso(text);
  return local !== null && (local.getDay() === 0 || local.getDay() === 6);
}
