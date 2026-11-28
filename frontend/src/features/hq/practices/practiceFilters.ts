import type { HqPractice } from "@/lib/api/types";
import { isClosed, isEndingSoon, isLive } from "../practiceStatus";

const PRACTICES_PATH = "/hq/practices";

export type PracticeFilter = "all" | "live" | "active" | "trial" | "ending" | "ended" | "blocked" | "closed";

export const PRACTICE_FILTERS: readonly PracticeFilter[] = ["all", "live", "active", "trial", "ending", "ended", "blocked", "closed"];

export function isPracticeFilter(value: string | null): value is PracticeFilter {
  return value !== null && (PRACTICE_FILTERS as readonly string[]).includes(value);
}

export function inPracticeFilter(practice: HqPractice, filter: PracticeFilter): boolean {
  if (filter === "all") return true;
  if (filter === "live") return isLive(practice);
  if (filter === "ending") return isEndingSoon(practice);
  if (filter === "closed") return isClosed(practice);
  return practice.status === filter;
}

export function countPractices(practices: HqPractice[], filter: PracticeFilter): number {
  return practices.filter((practice) => inPracticeFilter(practice, filter)).length;
}

export function practicesPath(filter: PracticeFilter): string {
  return filter === "all" ? PRACTICES_PATH : `${PRACTICES_PATH}?status=${filter}`;
}
