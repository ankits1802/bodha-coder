import type { BillingRow, BillingShow } from "@/lib/api/types";
import { localIsoDate } from "@/lib/dates";
import { formatDateTime, formatTime } from "@/lib/format";

export const BILLING_SHOWS: readonly BillingShow[] = ["ready", "exported", "all"];

export function isBillingShow(value: string | null): value is BillingShow {
  return value !== null && (BILLING_SHOWS as readonly string[]).includes(value);
}

export interface DayGroup {
  day: string;
  rows: BillingRow[];
}

export function groupByServiceDate(rows: BillingRow[]): DayGroup[] {
  const groups: DayGroup[] = [];
  for (const row of rows) {
    const last = groups[groups.length - 1];
    if (last && last.day === row.service_date) last.rows.push(row);
    else groups.push({ day: row.service_date, rows: [row] });
  }
  return groups;
}

export interface BillingSummary {
  visits: number;
  changed: number;
  asBilled: number;
}

export function summarise(rows: BillingRow[]): BillingSummary {
  const changed = rows.filter((row) => row.changed > 0).length;
  return { visits: rows.length, changed, asBilled: rows.length - changed };
}

export function momentLabel(instant: string, today: string): string {
  return localIsoDate(new Date(instant)) === today ? formatTime(instant) : formatDateTime(instant);
}
