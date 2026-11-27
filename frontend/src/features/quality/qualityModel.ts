import type { StatusTone } from "@/components/ui/StatusDot";
import type {
  AgreementSide,
  AgreementSummary,
  EligibilityReason,
  EvalRunChange,
  EvalRunStatus,
  LevelMix,
  LevelMixStatus,
  Role,
  SampleOverview,
  WilsonRate,
} from "@/lib/api/types";
import { QUALITY_TEXT } from "./strings";

export type QualityView = "audits" | "evaluation" | "autonomy";
export type Display = "chart" | "table";
export type RateKey = "em" | "icd_precision" | "icd_recall" | "icd_exact" | "modifiers";

export interface RateRow {
  key: RateKey;
  rate: WilsonRate;
}

export interface LevelShare {
  level: string;
  recent: number;
  prior: number;
  recentShare: number | null;
  priorShare: number | null;
}

export const QUALITY_VIEWS: readonly QualityView[] = ["audits", "evaluation", "autonomy"];
export const DISPLAYS: readonly Display[] = ["chart", "table"];
export const SIDES: readonly AgreementSide[] = ["bodha", "claim"];
export const RATE_KEYS: readonly RateKey[] = ["em", "icd_precision", "icd_recall", "icd_exact", "modifiers"];
export const QUALITY_ADMINS: readonly Role[] = ["admin"];
export const TREND_RUNS = 12;

export const ELIGIBILITY_TONES: Record<EligibilityReason, StatusTone> = {
  eligible: "ok",
  no_audit: "neutral",
  too_few_notes: "warn",
  agreement_low: "bad",
  too_many_higher: "bad",
};

export const LEVEL_MIX_TONES: Record<LevelMixStatus, StatusTone> = { steady: "ok", shifted: "warn", not_enough: "neutral" };

export const RUN_TONES: Record<EvalRunStatus, StatusTone> = { queued: "neutral", running: "neutral", done: "ok", failed: "bad" };

function pick<V extends string>(value: string | null, options: readonly V[], fallback: V): V {
  return options.find((option) => option === value) ?? fallback;
}

export function parseView(value: string | null): QualityView {
  return pick(value, QUALITY_VIEWS, "audits");
}

export function parseDisplay(value: string | null): Display {
  return pick(value, DISPLAYS, "chart");
}

export function parseSide(value: string | null): AgreementSide {
  return pick(value, SIDES, "bodha");
}

export function isQualityAdmin(role: Role | null | undefined): boolean {
  return role != null && QUALITY_ADMINS.includes(role);
}

export function rateRows(summary: AgreementSummary): RateRow[] {
  return RATE_KEYS.map((key) => ({ key, rate: summary[key] }));
}

export function scopeName(sample: SampleOverview): string {
  if (sample.scope === "provider") return sample.provider_name ?? QUALITY_TEXT.scopeLabels.provider;
  if (sample.scope === "specialty") return sample.specialty ?? QUALITY_TEXT.scopeLabels.specialty;
  return QUALITY_TEXT.scopeLabels.practice;
}

export function changeTone(change: EvalRunChange | null): StatusTone {
  if (change === null) return "neutral";
  return change.status === "dropped" ? "bad" : "ok";
}

function shareOf(count: number, total: number): number | null {
  return total > 0 ? count / total : null;
}

export function levelShares(mix: LevelMix): LevelShare[] {
  return mix.levels.map((row) => ({
    ...row,
    recentShare: shareOf(row.recent, mix.recent.notes),
    priorShare: shareOf(row.prior, mix.prior.notes),
  }));
}
