import type { QueryChanges } from "@/hooks/useQueryParams";
import type { AccessLogEntry, AccessLogFilters } from "@/lib/api/types";
import { isIsoDate } from "@/lib/dates";
import { SECURITY_TEXT } from "./strings";

export type FilterKey = keyof Required<AccessLogFilters>;
export type ResolvedFilters = { [Key in FilterKey]: string | null } & { start: string; end: string };

export const LOG_PARAMS: Record<FilterKey, string> = {
  start: "start",
  end: "end",
  user_id: "user",
  action: "action",
  note_id: "note",
  patient: "patient",
  birth_date: "born",
};

function firstMatch(agent: string, table: readonly (readonly [string, string])[]): string | null {
  const found = table.find(([marker]) => agent.includes(marker));
  return found ? found[1] : null;
}

export function deviceOf(entry: Pick<AccessLogEntry, "ip" | "user_agent">): string {
  const words = SECURITY_TEXT.devices;
  const agent = entry.user_agent ?? "";
  const parts = [firstMatch(agent, words.systems), firstMatch(agent, words.browsers), entry.ip].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : words.unknown;
}

export function accessLogFilters(get: (name: string) => string | null, today: string): ResolvedFilters {
  const day = (key: FilterKey): string | null => {
    const value = get(LOG_PARAMS[key]);
    return value && isIsoDate(value) ? value : null;
  };
  const text = (key: FilterKey): string | null => get(LOG_PARAMS[key])?.trim() || null;
  const start = day("start") ?? today;
  const end = day("end") ?? start;
  return {
    start,
    end: end < start ? start : end,
    user_id: text("user_id"),
    action: text("action"),
    note_id: text("note_id"),
    patient: text("patient"),
    birth_date: day("birth_date"),
  };
}

export function filterChanges(changes: Partial<ResolvedFilters>): QueryChanges {
  const entries = Object.entries(changes).map(([key, value]) => [LOG_PARAMS[key as FilterKey], value?.trim() || null]);
  return { ...Object.fromEntries(entries), offset: null };
}

export function filtersKey(filters: ResolvedFilters, offset: number): string {
  return ["access-log", ...Object.values(filters).map((value) => value ?? ""), String(offset)].join(":");
}
