import type { PracticeRole } from "@/lib/api/types";
import { isEmail } from "@/lib/validation";
import { INVITE_ROWS_TEXT } from "./strings";

export interface InviteRow {
  id: number;
  name: string;
  email: string;
  role: PracticeRole;
  failure: string | null;
}

export interface RowErrors {
  name?: string;
  email?: string;
}

export const FIRST_ROWS = 3;
const DEFAULT_ROLE: PracticeRole = "coder";

export function blankRow(id: number): InviteRow {
  return { id, name: "", email: "", role: DEFAULT_ROLE, failure: null };
}

export function blankRows(count: number): InviteRow[] {
  return Array.from({ length: count }, (_, index) => blankRow(index));
}

export function nextRowId(rows: readonly InviteRow[]): number {
  return rows.reduce((highest, row) => Math.max(highest, row.id), -1) + 1;
}

export function isBlank(row: InviteRow): boolean {
  return row.name.trim() === "" && row.email.trim() === "";
}

export function rowErrors(row: InviteRow): RowErrors {
  if (isBlank(row)) return {};
  const errors: RowErrors = {};
  if (!row.name.trim()) errors.name = INVITE_ROWS_TEXT.errors.name;
  if (!isEmail(row.email)) errors.email = INVITE_ROWS_TEXT.errors.email;
  return errors;
}

export function filledRows(rows: readonly InviteRow[]): InviteRow[] {
  return rows.filter((row) => !isBlank(row));
}

export function readyToSend(rows: readonly InviteRow[]): boolean {
  const filled = filledRows(rows);
  return filled.length > 0 && filled.every((row) => Object.keys(rowErrors(row)).length === 0);
}
