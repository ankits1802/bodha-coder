import type { TodaySummary } from "@/lib/api/types";

export const START_LANE = "coder";

export function reviewStart(summary: Pick<TodaySummary, "next_up">): string {
  const first = summary.next_up[0];
  return first ? `/notes/${encodeURIComponent(first.id)}?lane=${START_LANE}` : `/queue?lane=${START_LANE}`;
}
