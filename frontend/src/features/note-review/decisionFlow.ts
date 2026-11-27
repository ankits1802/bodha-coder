import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { CODE_KINDS, isCodeFinding, suspectedConditions } from "./findings";

export type DecisionTab = "codes" | "questions" | "risk";

function kindOrder(finding: Finding): number {
  return CODE_KINDS.indexOf(finding.kind);
}

export function codeFindings(findings: Finding[]): Finding[] {
  return findings.filter(isCodeFinding).sort((a, b) => kindOrder(a) - kindOrder(b));
}

export function questionFindings(findings: Finding[]): Finding[] {
  return findings.filter((finding) => finding.kind === "cdi_query" || (finding.kind === "diagnosis" && finding.action === "ask"));
}

export function isDecidable(finding: Finding): boolean {
  return finding.allowed.length >= 2;
}

const TAB_FINDINGS: Record<DecisionTab, (findings: Finding[]) => Finding[]> = {
  codes: codeFindings,
  questions: questionFindings,
  risk: suspectedConditions,
};

export function decisionOrder(findings: Finding[], tab: string): string[] {
  const pick = TAB_FINDINGS[tab as DecisionTab];
  return pick ? pick(findings).filter(isDecidable).map((finding) => finding.key) : [];
}

export function nextInOrder(order: string[], key: string): string | null {
  const at = order.indexOf(key);
  return at >= 0 ? (order[at + 1] ?? null) : (order[0] ?? null);
}

export function choiceFor(finding: Finding, accept: boolean): Choice | null {
  if (!isDecidable(finding)) return null;
  return finding.allowed[accept ? 0 : 1] ?? null;
}

export function withChoice(detail: NoteDetail, key: string, choice: Choice): NoteDetail {
  return {
    ...detail,
    findings: detail.findings.map((finding) => (finding.key === key ? { ...finding, choice } : finding)),
  };
}
