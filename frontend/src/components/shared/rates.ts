import type { Rate } from "@/lib/api/types";
import { FORMAT_WORDS, formatPercent } from "@/lib/format";

export const RATE_TEXT = {
  interval: (low: string, high: string) => `${low}–${high}`,
  withInterval: (value: string, interval: string) => `${value} (${interval})`,
  counted: (successes: string, trials: string) => `${successes} of ${trials}`,
} as const;

export function formatInterval(rate: Rate): string {
  if (rate.low === null || rate.high === null) return FORMAT_WORDS.empty;
  return RATE_TEXT.interval(formatPercent(rate.low), formatPercent(rate.high));
}

export function formatRate(rate: Rate): string {
  if (rate.value === null) return FORMAT_WORDS.empty;
  return RATE_TEXT.withInterval(formatPercent(rate.value), formatInterval(rate));
}

export function formatCounted(rate: Rate): string {
  return RATE_TEXT.counted(String(rate.successes), String(rate.trials));
}
