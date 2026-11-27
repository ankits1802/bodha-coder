import type { StatusTone } from "@/components/ui/StatusDot";
import type { DayFlag, ProviderDay } from "@/lib/api/types";
import { formatCount, formatMinutes, formatPercent } from "@/lib/format";
import { DAY_TEXT } from "./strings";

export const FLAG_TONES: Record<DayFlag, StatusTone> = {
  time_over_day: "warn",
  cloned_text: "bad",
  high_level_share: "warn",
};

export function clonedWith(day: ProviderDay, noteId: string): Set<string> {
  const partners = new Set<string>();
  for (const pair of day.duplicates) {
    if (pair.first === noteId) partners.add(pair.second);
    if (pair.second === noteId) partners.add(pair.first);
  }
  return partners;
}

export function dayFacts(day: ProviderDay): string[] {
  const facts = [DAY_TEXT.notes(formatCount(day.notes.length), day.notes.length)];
  if (day.timed_notes > 0) facts.push(DAY_TEXT.documented(formatMinutes(day.total_minutes)));
  if (day.high_level_share !== null) facts.push(DAY_TEXT.topLevels(formatPercent(day.high_level_share)));
  if (day.duplicates.length > 0) facts.push(DAY_TEXT.clonePairs(formatCount(day.duplicates.length), day.duplicates.length));
  return facts;
}

export function noteHref(noteId: string): string {
  return `/notes/${encodeURIComponent(noteId)}`;
}
