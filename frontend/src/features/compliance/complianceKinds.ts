import type { NoteDetail, QueueRow } from "@/lib/api/types";

export type ComplianceKind = "all" | "too_high" | "risk" | "flagged";
export const COMPLIANCE_KINDS: readonly ComplianceKind[] = ["all", "too_high", "risk", "flagged"];

const FLAGGED_HEADLINE = "Flagged for compliance";
const RISK_HEADLINE = "High audit risk";

export function isComplianceKind(value: string | null): value is ComplianceKind {
  return value !== null && (COMPLIANCE_KINDS as readonly string[]).includes(value);
}

export function kindOf(row: QueueRow): Exclude<ComplianceKind, "all"> {
  if (row.headline === FLAGGED_HEADLINE) return "flagged";
  if (row.headline === RISK_HEADLINE) return "risk";
  return "too_high";
}

export function inKind(row: QueueRow, kind: ComplianceKind): boolean {
  return kind === "all" || kindOf(row) === kind;
}

export function countByKind(rows: QueueRow[]): Record<ComplianceKind, number> {
  const counts: Record<ComplianceKind, number> = { all: rows.length, too_high: 0, risk: 0, flagged: 0 };
  for (const row of rows) counts[kindOf(row)] += 1;
  return counts;
}

export interface CaseFacts {
  billed: string | null;
  supported: string | null;
  inTheNote: string[];
  flagReason: string | null;
  risks: { severity: string | null; title: string }[];
}

function mdmReasons(detail: Record<string, unknown>): string[] {
  const elements = detail.mdm_elements;
  if (!elements || typeof elements !== "object") return [];
  return ["problems", "data", "risk"]
    .map((name) => (elements as Record<string, unknown>)[name])
    .map((element) => (element && typeof element === "object" ? (element as Record<string, unknown>).reason : null))
    .filter((reason): reason is string => typeof reason === "string" && reason.trim().length > 0);
}

export function caseFacts(note: NoteDetail): CaseFacts {
  const em = note.findings.find((finding) => finding.kind === "em");
  const reasons = em ? mdmReasons(em.detail) : [];
  return {
    billed: em?.code_before ?? null,
    supported: em?.code_after ?? null,
    inTheNote: reasons.length > 0 ? reasons : (em?.evidence ?? []),
    flagReason: note.note.flag_reason,
    risks: note.findings
      .filter((finding) => finding.kind === "audit_risk")
      .map((finding) => ({ severity: finding.severity, title: finding.title })),
  };
}
