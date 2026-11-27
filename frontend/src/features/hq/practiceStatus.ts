import type { StatusTone } from "@/components/ui/StatusDot";
import type { HqPractice, PracticeStatus } from "@/lib/api/types";
import { isoDateInZone, localDateFromIso } from "@/lib/dates";
import { formatCalendarDay } from "@/lib/format";
import { PRACTICE_STATUS_LABELS } from "@/lib/labels";
import { HQ_TEXT } from "./strings";

export const ENDING_SOON_DAYS = 14;
const DAY = 86_400_000;

const STATUS_TONES: Record<PracticeStatus, StatusTone> = {
  active: "ok",
  trial: "low",
  ended: "bad",
  blocked: "bad",
  closed: "neutral",
  purged: "neutral",
};

type Renewal = Pick<HqPractice, "renews_on" | "time_zone">;

export function practiceToday(practice: Pick<HqPractice, "time_zone">, now: Date = new Date()): string {
  return isoDateInZone(now, practice.time_zone);
}

export function daysUntil(isoDate: string, today: string): number | null {
  const target = localDateFromIso(isoDate);
  const start = localDateFromIso(today);
  if (!target || !start) return null;
  return Math.round((target.getTime() - start.getTime()) / DAY);
}

export function daysLeft(practice: Renewal, today: string = practiceToday(practice)): number | null {
  return practice.renews_on ? daysUntil(practice.renews_on, today) : null;
}

export function isLive(practice: Pick<HqPractice, "status">): boolean {
  return practice.status === "active" || practice.status === "trial";
}

export function isClosed(practice: Pick<HqPractice, "status">): boolean {
  return practice.status === "closed" || practice.status === "purged";
}

export function isEndingSoon(practice: Pick<HqPractice, "status"> & Renewal, today?: string): boolean {
  if (!isLive(practice)) return false;
  const days = daysLeft(practice, today);
  return days !== null && days <= ENDING_SOON_DAYS;
}

export function practiceStatusView(practice: HqPractice, today?: string): { tone: StatusTone; label: string } {
  if (isEndingSoon(practice, today)) return { tone: "warn", label: HQ_TEXT.status.endingSoon };
  return { tone: STATUS_TONES[practice.status], label: PRACTICE_STATUS_LABELS[practice.status] };
}

export function renewalLine(practice: HqPractice, today?: string): string {
  const words = HQ_TEXT.status;
  if (practice.status === "purged") return words.purged(practice.purged_at ? formatCalendarDay(practice.purged_at.slice(0, 10), "year") : "").trim();
  if (practice.status === "closed" && practice.purge_after) return words.purgeAfter(formatCalendarDay(practice.purge_after, "year"));
  if (!practice.renews_on) return words.noRenewal;
  const day = formatCalendarDay(practice.renews_on, "year");
  if (practice.status === "ended") return words.ended(day);
  return isEndingSoon(practice, today) ? words.ends(day) : words.renews(day);
}
