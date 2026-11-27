import type { Finding, NoteDetail } from "@/lib/api/types";
import { CODE_KINDS, COMPLIANCE_SEVERITY, SEVERITY_ORDER, isCodeFinding, isQuestion } from "./findings";

export type ReviewFilter = "all" | "changes" | "questions" | "risk" | "guidance";
export type ReviewCategory = Exclude<ReviewFilter, "all">;
export type ReviewGroupKey = "blocking" | ReviewCategory;

export const REVIEW_FILTERS: readonly ReviewFilter[] = ["all", "changes", "questions", "risk", "guidance"];
export const GROUP_ORDER: readonly ReviewGroupKey[] = ["blocking", "changes", "questions", "risk", "guidance"];

export interface ReviewRow {
  finding: Finding;
  category: ReviewCategory;
  wording: Finding[];
}

export type ReviewGroups = Record<ReviewGroupKey, ReviewRow[]> & { supported: Finding[] };

const SUSPECTED_PREFIX = "hcc:";

function categoryOf(finding: Finding): ReviewCategory | null {
  if (finding.key.startsWith(SUSPECTED_PREFIX) || finding.kind === "audit_risk") return "risk";
  if (isQuestion(finding)) return "questions";
  if (isCodeFinding(finding)) return "changes";
  if (finding.kind === "cdi_gap" || finding.kind === "audit_finding") return "guidance";
  return null;
}

export function isBlocking(finding: Finding, detail: Pick<NoteDetail, "note">): boolean {
  if (finding.override_needed || finding.decide_again) return true;
  if (finding.action === "review" && finding.code_before !== null) return true;
  return finding.kind === "audit_risk" && finding.severity === COMPLIANCE_SEVERITY && detail.note.lane === "compliance";
}

export function isSupported(finding: Finding): boolean {
  return isCodeFinding(finding) && finding.action === "keep" && !finding.override_needed && !finding.decide_again;
}

function wordingFor(finding: Finding, gaps: Finding[]): Finding[] {
  if (!isCodeFinding(finding)) return [];
  const codes = [finding.code_before, finding.code_after].filter((code): code is string => code !== null);
  return gaps.filter((gap) => codes.some((code) => code === gap.code_before || code === gap.code_after));
}

function dollars(finding: Finding): number {
  return finding.amount_change === null ? -1 : Math.abs(finding.amount_change);
}

function kindRank(finding: Finding): number {
  const at = CODE_KINDS.indexOf(finding.kind);
  return at < 0 ? CODE_KINDS.length : at;
}

function severityRank(finding: Finding): number {
  const at = SEVERITY_ORDER.indexOf(finding.severity ?? "");
  return at < 0 ? SEVERITY_ORDER.length : at;
}

export function byImpact(a: ReviewRow, b: ReviewRow): number {
  return dollars(b.finding) - dollars(a.finding) || kindRank(a.finding) - kindRank(b.finding);
}

function byRisk(a: ReviewRow, b: ReviewRow): number {
  const audit = (row: ReviewRow) => (row.finding.kind === "audit_risk" ? 1 : 0);
  return audit(a) - audit(b) || (audit(a) === 1 ? severityRank(a.finding) - severityRank(b.finding) : 0);
}

function byGuidance(a: ReviewRow, b: ReviewRow): number {
  const kinds = (row: ReviewRow) => (row.finding.kind === "cdi_gap" ? 0 : 1);
  return kinds(a) - kinds(b) || severityRank(a.finding) - severityRank(b.finding);
}

function emptyGroups(): ReviewGroups {
  return { blocking: [], changes: [], questions: [], risk: [], guidance: [], supported: [] };
}

export function reviewGroups(detail: Pick<NoteDetail, "note" | "findings">): ReviewGroups {
  const gaps = detail.findings.filter((finding) => finding.kind === "cdi_gap");
  const attached = new Set<string>();
  const groups = emptyGroups();
  for (const finding of detail.findings) {
    const category = categoryOf(finding);
    if (category === null || finding.kind === "cdi_gap") continue;
    if (isSupported(finding)) {
      groups.supported.push(finding);
      continue;
    }
    const wording = wordingFor(finding, gaps);
    wording.forEach((gap) => attached.add(gap.key));
    groups[isBlocking(finding, detail) ? "blocking" : category].push({ finding, category, wording });
  }
  const loose = gaps.filter((gap) => !attached.has(gap.key));
  groups.guidance.push(...loose.map((gap): ReviewRow => ({ finding: gap, category: "guidance", wording: [] })));
  groups.blocking.sort(byImpact);
  groups.changes.sort(byImpact);
  groups.risk.sort(byRisk);
  groups.guidance.sort(byGuidance);
  return groups;
}

export function groupRows(groups: ReviewGroups, group: ReviewGroupKey, filter: ReviewFilter): ReviewRow[] {
  const rows = groups[group];
  return filter === "all" ? rows : rows.filter((row) => row.category === filter);
}

export function visibleRows(groups: ReviewGroups, filter: ReviewFilter): ReviewRow[] {
  return GROUP_ORDER.flatMap((group) => groupRows(groups, group, filter));
}

export function showsSupported(filter: ReviewFilter): boolean {
  return filter === "all" || filter === "changes";
}

export function filterCounts(groups: ReviewGroups): Record<ReviewFilter, number> {
  const rows = visibleRows(groups, "all");
  const count = (category: ReviewCategory) => rows.filter((row) => row.category === category).length;
  return { all: rows.length, changes: count("changes"), questions: count("questions"), risk: count("risk"), guidance: count("guidance") };
}

export function supportedToAccept(groups: ReviewGroups): Finding[] {
  return groups.supported.filter((finding) => {
    const accepting = finding.allowed[0];
    return !finding.decided && accepting !== undefined && !finding.departing_choices.includes(accepting);
  });
}
