import type { StatusTone } from "@/components/ui/StatusDot";
import type { Choice, CodeJson, Finding, FindingAction, FindingKind, MdmElements, NoteHistory, NoteText } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { containsQuote, type HighlightTone, type Mark } from "@/lib/highlight";
import { REVIEW_TEXT } from "./strings";

export const CODE_KINDS: readonly FindingKind[] = ["em", "modifier", "code_review", "diagnosis"];
const QUESTION_KINDS: readonly FindingKind[] = ["cdi_query", "diagnosis"];
const CHANGE_KINDS: readonly FindingKind[] = ["em", "diagnosis", "code_review", "modifier"];
const CHANGE_ACTIONS: readonly FindingAction[] = ["lower", "raise", "replace", "add", "remove", "review"];
const SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"];

const SUPPORTING: readonly FindingAction[] = ["keep", "add", "lower", "raise", "replace"];
const NEEDS_DETAIL: readonly FindingAction[] = ["ask", "review"];

export function highlightTone(finding: Pick<Finding, "kind" | "action">): HighlightTone | null {
  if (SUPPORTING.includes(finding.action)) return "ok";
  if (NEEDS_DETAIL.includes(finding.action)) return "warn";
  if (finding.action === "remove") return "bad";
  if (finding.action === "info" && finding.kind === "cdi_gap") return "warn";
  return null;
}

export function marksFor(findings: Finding[]): Mark[] {
  return findings.flatMap((finding) => {
    const tone = highlightTone(finding);
    return tone ? finding.evidence.map((quote) => ({ quote, tone })) : [];
  });
}

export interface FindingStatus {
  tone: StatusTone;
  label: string;
}

const EM_STATUS: Partial<Record<FindingAction, FindingStatus>> = {
  lower: { tone: "bad", label: REVIEW_TEXT.status.tooHigh },
  raise: { tone: "low", label: REVIEW_TEXT.status.tooLow },
  keep: { tone: "ok", label: REVIEW_TEXT.status.matches },
  replace: { tone: "bad", label: REVIEW_TEXT.status.otherFamily },
  add: { tone: "dark", label: REVIEW_TEXT.status.addVisit },
};

const CODE_STATUS: Partial<Record<FindingAction, FindingStatus>> = {
  keep: { tone: "ok", label: REVIEW_TEXT.status.supported },
  ask: { tone: "warn", label: REVIEW_TEXT.status.needsDetail },
  remove: { tone: "bad", label: REVIEW_TEXT.status.notSupported },
  replace: { tone: "ok", label: REVIEW_TEXT.status.replace },
  add: { tone: "ok", label: REVIEW_TEXT.status.add },
};

export function findingStatus(finding: Pick<Finding, "kind" | "action">): FindingStatus {
  if (finding.kind === "em") return EM_STATUS[finding.action] ?? { tone: "warn", label: REVIEW_TEXT.status.unconfirmed };
  if (finding.action === "review") {
    const label = finding.kind === "diagnosis" ? REVIEW_TEXT.status.notBillable : REVIEW_TEXT.status.unconfirmed;
    return { tone: "warn", label };
  }
  return CODE_STATUS[finding.action] ?? { tone: "neutral", label: REVIEW_TEXT.status.info };
}

export const RISK_SUMMARY_KEY = "hcc";
const SUSPECTED_PREFIX = "hcc:";

export function isRiskFinding(finding: Pick<Finding, "key">): boolean {
  return finding.key === RISK_SUMMARY_KEY || finding.key.startsWith(SUSPECTED_PREFIX);
}

export function isCodeFinding(finding: Finding): boolean {
  return CODE_KINDS.includes(finding.kind) && !isRiskFinding(finding);
}

export function suspectedConditions(findings: Finding[]): Finding[] {
  return findings.filter((item) => item.key.startsWith(SUSPECTED_PREFIX));
}

export type RiskStatus = "captured" | "missed" | "unsupported";
const RISK_STATUSES: readonly RiskStatus[] = ["captured", "missed", "unsupported"];

export interface RiskCategory {
  hcc: string;
  label: string;
  status: RiskStatus;
  codes: string[];
  factor: number | null;
}

export interface RiskSummary {
  available: boolean;
  model: string | null;
  paymentYear: string | null;
  segment: string | null;
  ageFromNote: boolean;
  scoreBilled: number | null;
  scoreDocumented: number | null;
  categories: RiskCategory[];
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function riskCategory(value: unknown): RiskCategory | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  const status = RISK_STATUSES.find((item) => item === row.status);
  const hcc = textValue(row.hcc);
  if (!status || !hcc) return null;
  return { hcc, label: textValue(row.label) ?? hcc, status, codes: stringList(row.codes), factor: numberValue(row.factor) };
}

export function riskSummary(findings: Finding[]): RiskSummary | null {
  const summary = findings.find((item) => item.key === RISK_SUMMARY_KEY);
  if (!summary) return null;
  const detail = summary.detail;
  const rows = Array.isArray(detail.categories) ? detail.categories : [];
  return {
    available: detail.available === true,
    model: textValue(detail.model),
    paymentYear: textValue(detail.payment_year),
    segment: textValue(detail.segment),
    ageFromNote: detail.age_from === "note",
    scoreBilled: numberValue(detail.score_billed),
    scoreDocumented: numberValue(detail.score_documented),
    categories: rows.map(riskCategory).filter((row): row is RiskCategory => row !== null),
  };
}

export function formatRiskScore(value: number | null): string {
  return value === null ? FORMAT_WORDS.empty : value.toFixed(3);
}

export type MeasureStatus = "met" | "missing" | "not_applicable";
const MEASURE_STATUSES: readonly MeasureStatus[] = ["met", "missing", "not_applicable"];

export function measureStatus(finding: Finding): MeasureStatus | null {
  return MEASURE_STATUSES.find((status) => status === finding.detail.status) ?? null;
}

export function openQuestions(findings: Finding[]): Finding[] {
  return findings.filter((item) => QUESTION_KINDS.includes(item.kind) && item.action === "ask" && item.choice === "ask");
}

export function codeChangeCount(findings: Finding[]): number {
  return findings.filter((item) => CHANGE_KINDS.includes(item.kind) && CHANGE_ACTIONS.includes(item.action)).length;
}

export function highestAuditRisk(findings: Finding[]): string | null {
  const severities = findings.filter((item) => item.kind === "audit_risk" && item.severity).map((item) => item.severity ?? "");
  return SEVERITY_ORDER.find((level) => severities.includes(level)) ?? null;
}

export function choiceLabel(finding: Pick<Finding, "code_before">, choice: Choice): string {
  if (choice === "keep" && finding.code_before) return REVIEW_TEXT.keepCode(finding.code_before);
  return REVIEW_TEXT.choices[choice];
}

const UNITS_SIGN = "×";

export function withUnits(label: string, units: number | undefined): string {
  return units !== undefined && units > 1 ? `${label} ${UNITS_SIGN}${units}` : label;
}

export function codeLabel(code: CodeJson): string {
  return withUnits([code.code, ...code.modifiers].join("-"), code.units);
}

export function codeAfterLabel(finding: Pick<Finding, "code_after" | "detail">): string | null {
  const units = typeof finding.detail.units === "number" ? finding.detail.units : undefined;
  return finding.code_after === null ? null : withUnits(finding.code_after, units);
}

export type QuoteCheck = "found" | "missing";

export function quoteCheck(finding: Pick<Finding, "evidence">, texts: NoteText[]): QuoteCheck | null {
  const quotes = finding.evidence.filter((quote) => quote.trim() !== "");
  if (quotes.length === 0 || texts.length === 0) return null;
  const found = quotes.every((quote) => texts.some((text) => containsQuote(text.text, quote)));
  return found ? "found" : "missing";
}

export function quoteStatus(check: QuoteCheck): FindingStatus {
  return check === "found"
    ? { tone: "ok", label: REVIEW_TEXT.quote.found }
    : { tone: "warn", label: REVIEW_TEXT.quote.missing };
}

export function latestBilled(history: NoteHistory): CodeJson[] {
  const billed = history.code_sets.filter((set) => set.kind === "billed");
  const latest = billed.reduce<(typeof billed)[number] | null>(
    (best, set) => (best === null || set.revision > best.revision ? set : best),
    null,
  );
  return latest?.codes ?? [];
}

export function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "") : [];
}

export function textValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

export interface EmDetail {
  mdm: MdmElements | null;
  basis: string | null;
  timeMinutes: number | null;
  nextLevelNeeds: string[];
  alternativeCode: string | null;
}

function isMdm(value: unknown): value is MdmElements {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return ["problems", "data", "risk"].every((part) => {
    const element = record[part] as Record<string, unknown> | undefined;
    return typeof element?.level === "string";
  });
}

export function emDetail(finding: Finding): EmDetail {
  const detail = finding.detail;
  return {
    mdm: isMdm(detail.mdm_elements) ? detail.mdm_elements : null,
    basis: textValue(detail.basis),
    timeMinutes: typeof detail.time_minutes === "number" ? detail.time_minutes : null,
    nextLevelNeeds: stringList(detail.next_level_needs),
    alternativeCode: textValue(detail.alternative_code),
  };
}
