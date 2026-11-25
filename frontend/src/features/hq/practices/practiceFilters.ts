import type { HqPractice } from "@/lib/api/types";
import { isEndingSoon } from "../practiceStatus";

export type PracticeFilter = "all" | "active" | "trial" | "ending" | "ended" | "blocked";

export const PRACTICE_FILTERS: readonly PracticeFilter[] = ["all", "active", "trial", "ending", "ended", "blocked"];

export function isPracticeFilter(value: string | null): value is PracticeFilter {
  return value !== null && (PRACTICE_FILTERS as readonly string[]).includes(value);
}

export function inPracticeFilter(practice: HqPractice, filter: PracticeFilter): boolean {
  if (filter === "all") return true;
  if (filter === "ending") return isEndingSoon(practice);
  return practice.status === filter;
}

export function countPractices(practices: HqPractice[], filter: PracticeFilter): number {
  return practices.filter((practice) => inPracticeFilter(practice, filter)).length;
}
