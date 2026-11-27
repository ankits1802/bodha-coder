import type { StatusTone } from "@/components/ui/StatusDot";
import type { ActivityChange, AuditChain, HqActivityEntry } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
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

export function actionChoices(actions: readonly string[], current: string | null): string[] {
  return current && !actions.includes(current) ? [...actions, current].sort() : [...actions];
}

export function matchesSearch(entry: HqActivityEntry, search: string, names: Map<string, string>): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  const haystack = [entry.actor, entry.action, entry.detail ?? "", practiceLabel(entry.practice_id, names)];
  return haystack.some((value) => value.toLowerCase().includes(needle));
}

function shownValue(value: string | number | null): string {
  return value === null ? HQ_TEXT.activity.notSet : String(value);
}

export function changeLines(changes: ActivityChange[] | null): string[] {
  const words = HQ_TEXT.activity;
  return (changes ?? []).map((change) =>
    words.change(words.fields[change.field] ?? change.field, shownValue(change.before), shownValue(change.after)),
  );
}

export function activityCsv(entries: HqActivityEntry[], names: Map<string, string>): string {
  const rows = entries.map((entry) => [
    entry.at,
    entry.action,
    practiceLabel(entry.practice_id, names),
    entry.detail,
    changeLines(entry.changes).join("; "),
    entry.actor,
  ]);
  return toCsv([...HQ_TEXT.activity.csvHeader], rows);
}

export function brokenChainLine(chain: AuditChain): string {
  const words = HQ_TEXT.activity.check;
  const where = chain.chain === "activity" ? words.hqActivity : (chain.practice_name ?? words.unknownPractice);
  const problem = chain.problem ? words.problems[chain.problem] : "";
  return words.at(where, formatCount(chain.broken_seq ?? 0), problem);
}
