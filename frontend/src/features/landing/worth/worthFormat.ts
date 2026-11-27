import { formatCount, formatMoney, formatPercent } from "@/lib/format";
import type { WorthField } from "./estimate";

const PERCENT = 100;

function percentOf(value: number): string {
  return formatPercent(value / PERCENT);
}

export const WORTH_FORMATS: Record<WorthField, (value: number) => string> = {
  visits: formatCount,
  lowPercent: percentOf,
  highPercent: percentOf,
  difference: formatMoney,
};

export type Affix = "dollars" | "percent" | null;

export const WORTH_AFFIXES: Record<WorthField, { prefix: Affix; suffix: Affix }> = {
  visits: { prefix: null, suffix: null },
  lowPercent: { prefix: null, suffix: "percent" },
  highPercent: { prefix: null, suffix: "percent" },
  difference: { prefix: "dollars", suffix: null },
};
