import type { QueueRow } from "@/lib/api/types";
import { addDays, localIsoDate } from "@/lib/dates";
import { formatCalendarDay } from "@/lib/format";
import { QUEUE_TEXT } from "./strings";

export interface RowGroup {
  key: string;
  dueDay: string;
  serviceDate: string;
  rows: QueueRow[];
}

export function groupRows(rows: QueueRow[]): RowGroup[] {
  const groups: RowGroup[] = [];
  for (const row of rows) {
    const dueDay = localIsoDate(new Date(row.due_at));
    const key = `${dueDay}|${row.service_date}`;
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.rows.push(row);
    else groups.push({ key, dueDay, serviceDate: row.service_date, rows: [row] });
  }
  return groups;
}

export function dueLabel(dueDay: string, today: string): string {
  if (dueDay < today) return QUEUE_TEXT.overdue;
  if (dueDay === today) return QUEUE_TEXT.dueToday;
  if (dueDay === addDays(today, 1)) return QUEUE_TEXT.dueTomorrow;
  return QUEUE_TEXT.dueOn(formatCalendarDay(dueDay));
}

export function groupLabel(group: RowGroup, today: string): string {
  return QUEUE_TEXT.groupLabel(dueLabel(group.dueDay, today), formatCalendarDay(group.serviceDate));
}
