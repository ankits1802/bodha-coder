import type { StatusTone } from "@/components/ui/StatusDot";
import type { HqPractice, PracticeStatus } from "@/lib/api/types";
import { localDateFromIso, localIsoDate } from "@/lib/dates";
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
};

export function daysUntil(isoDate: string, today: string = localIsoDate()): number | null {
  const target = localDateFromIso(isoDate);
  const start = localDateFromIso(today);
  if (!target || !start) return null;
  return Math.round((target.getTime() - start.getTime()) / DAY);
}

export function isLive(practice: Pick<HqPractice, "status">): boolean {
  return practice.status === "active" || practice.status === "trial";
}

export function isEndingSoon(practice: Pick<HqPractice, "status" | "renews_on">, today?: string): boolean {
  if (!isLive(practice) || !practice.renews_on) return false;
  const days = daysUntil(practice.renews_on, today);
  return days !== null && days <= ENDING_SOON_DAYS;
}

export function practiceStatusView(practice: HqPractice, today?: string): { tone: StatusTone; label: string } {
  if (isEndingSoon(practice, today)) return { tone: "warn", label: HQ_TEXT.status.endingSoon };
  return { tone: STATUS_TONES[practice.status], label: PRACTICE_STATUS_LABELS[practice.status] };
}

export function renewalLine(practice: HqPractice, today?: string): string {
  const words = HQ_TEXT.status;
  if (!practice.renews_on) return words.noRenewal;
  const day = formatCalendarDay(practice.renews_on, "year");
  if (practice.status === "ended") return words.ended(day);
  return isEndingSoon(practice, today) ? words.ends(day) : words.renews(day);
}
