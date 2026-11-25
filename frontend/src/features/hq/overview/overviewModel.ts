import type { StatusTone } from "@/components/ui/StatusDot";
import type { HqPractice } from "@/lib/api/types";
import { daysUntil, isLive } from "../practiceStatus";
import { HQ_TEXT } from "../strings";

export interface AttentionItem {
  practice: HqPractice;
  tone: StatusTone;
  reason: string;
}

const WINDOW_DAYS = 14;
const BUSIEST_LIMIT = 5;

function renewalReason(practice: HqPractice): AttentionItem | null {
  const words = HQ_TEXT.overview;
  if (!isLive(practice) || !practice.renews_on) return null;
  const days = daysUntil(practice.renews_on);
  if (days === null || days > WINDOW_DAYS) return null;
  if (days < 0) return { practice, tone: "bad", reason: words.renewalPassed };
  return { practice, tone: "warn", reason: days === 0 ? words.endsToday : words.endsIn(days) };
}

function failureReason(practice: HqPractice): AttentionItem | null {
  if (practice.failed_24h === 0) return null;
  return { practice, tone: "bad", reason: HQ_TEXT.overview.couldNotRead(practice.failed_24h, practice.last_failure) };
}

export function attentionItems(practices: HqPractice[]): AttentionItem[] {
  return practices
    .flatMap((practice) => [
      failureReason(practice),
      practice.status === "blocked" ? { practice, tone: "bad" as const, reason: HQ_TEXT.overview.blocked } : renewalReason(practice),
    ])
    .filter((item): item is AttentionItem => item !== null);
}

export function busiest(practices: HqPractice[]): HqPractice[] {
  return practices
    .filter((practice) => practice.waiting > 0)
    .sort((a, b) => b.waiting - a.waiting)
    .slice(0, BUSIEST_LIMIT);
}
