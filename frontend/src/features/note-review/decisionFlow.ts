import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import type { ReviewRow } from "./reviewList";

export function isDecidable(finding: Finding): boolean {
  return finding.allowed.length >= 2;
}

export function decisionOrder(rows: ReviewRow[]): string[] {
  return rows.filter((row) => isDecidable(row.finding)).map((row) => row.finding.key);
}

export function nextInOrder(order: string[], key: string): string | null {
  const at = order.indexOf(key);
  return at >= 0 ? (order[at + 1] ?? null) : (order[0] ?? null);
}

export function stepInOrder(order: string[], key: string | null, step: 1 | -1): string | null {
  if (key === null) return step === -1 ? (order.at(-1) ?? null) : null;
  const at = order.indexOf(key);
  if (at < 0) return order[0] ?? null;
  return order[Math.max(at + step, 0)] ?? null;
}

export function choiceFor(finding: Finding, accept: boolean): Choice | null {
  if (!isDecidable(finding)) return null;
  return finding.allowed[accept ? 0 : 1] ?? null;
}

export function shownChoice(finding: Finding): Choice | null {
  return finding.decide_again ? null : finding.choice;
}

export function withChoices(detail: NoteDetail, choices: Record<string, Choice>): NoteDetail {
  return {
    ...detail,
    findings: detail.findings.map((finding) => {
      const choice = choices[finding.key];
      return choice ? { ...finding, choice, decided: true, decide_again: false } : finding;
    }),
  };
}

export function withChoice(detail: NoteDetail, key: string, choice: Choice): NoteDetail {
  return withChoices(detail, { [key]: choice });
}
