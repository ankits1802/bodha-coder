import type { InsightDays } from "@/lib/api/types";

export const INSIGHT_DAYS: readonly InsightDays[] = [7, 14, 30, 90];

export function parseDays(value: string | null, fallback: InsightDays): InsightDays {
  const days = Number(value);
  return INSIGHT_DAYS.find((choice) => choice === days) ?? fallback;
}
