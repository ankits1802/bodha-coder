import type { StatusTone } from "@/components/ui/StatusDot";
import type { EmMixFamily, EmMixLevel } from "@/lib/api/types";
import { FORMAT_WORDS, formatPercent } from "@/lib/format";
import { EM_MIX_TEXT } from "./strings";

const P_FLOOR = 0.001;
const pointsFormat = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1, signDisplay: "exceptZero" });
const decimalsFormat = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 3 });

export interface FamilyStatus {
  tone: StatusTone;
  label: string;
}

export function familyStatus(family: EmMixFamily): FamilyStatus {
  if (!family.has_benchmark) return { tone: "neutral", label: EM_MIX_TEXT.noCmsData };
  if (family.outlier && family.lean === "higher") return { tone: "warn", label: EM_MIX_TEXT.higher };
  if (family.outlier && family.lean === "lower") return { tone: "low", label: EM_MIX_TEXT.lower };
  return { tone: "ok", label: EM_MIX_TEXT.inLine };
}

export function formatPoints(points: number | null): string {
  return points === null ? FORMAT_WORDS.empty : EM_MIX_TEXT.points(pointsFormat.format(points));
}

export function benchmarkShare(level: EmMixLevel): string {
  return level.benchmark === null ? FORMAT_WORDS.empty : formatPercent(level.benchmark);
}

export function testLine(family: EmMixFamily): string | null {
  if (family.chi_square === null || family.p_value === null || family.degrees_of_freedom === null) return null;
  const p = family.p_value < P_FLOOR ? EM_MIX_TEXT.pBelow : EM_MIX_TEXT.pValue(decimalsFormat.format(family.p_value));
  return EM_MIX_TEXT.test(decimalsFormat.format(family.chi_square), String(family.degrees_of_freedom), p);
}

export function barWidth(share: number | null): string {
  return `${Math.max(0, Math.min(1, share ?? 0)) * 100}%`;
}
