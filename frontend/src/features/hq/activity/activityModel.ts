import type { StatusTone } from "@/components/ui/StatusDot";
import type { HqActivityEntry } from "@/lib/api/types";
import { toCsv } from "@/lib/download";
import { HQ_TEXT } from "../strings";

const ACTION_TONES: Record<string, StatusTone> = {
  "practice added": "ok",
  "member invited": "ok",
  "providers imported": "ok",
};

export function actionTone(action: string): StatusTone {
  return ACTION_TONES[action] ?? "neutral";
}

export function actionLabel(action: string): string {
  return action.charAt(0).toUpperCase() + action.slice(1);
}

export function practiceLabel(practiceId: string | null, names: Map<string, string>): string {
  if (!practiceId) return HQ_TEXT.activity.allPractices;
  return names.get(practiceId) ?? practiceId;
}

export function actionsIn(entries: HqActivityEntry[]): string[] {
  return [...new Set(entries.map((entry) => entry.action))].sort();
}

export interface ActivityFilter {
  search: string;
  action: string | null;
}

export function matchesFilter(entry: HqActivityEntry, filter: ActivityFilter, names: Map<string, string>): boolean {
  if (filter.action && entry.action !== filter.action) return false;
  const needle = filter.search.trim().toLowerCase();
  if (!needle) return true;
  const haystack = [entry.actor, entry.action, entry.detail ?? "", practiceLabel(entry.practice_id, names)];
  return haystack.some((value) => value.toLowerCase().includes(needle));
}

export function activityCsv(entries: HqActivityEntry[], names: Map<string, string>): string {
  const rows = entries.map((entry) => [entry.at, entry.action, practiceLabel(entry.practice_id, names), entry.detail, entry.actor]);
  return toCsv([...HQ_TEXT.activity.csvHeader], rows);
}
