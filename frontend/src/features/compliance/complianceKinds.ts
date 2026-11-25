import type { ComplianceRow, LaneReason, NoteDetail } from "@/lib/api/types";

export type ComplianceKind = "all" | "too_high" | "risk" | "flagged";
export const COMPLIANCE_KINDS: readonly ComplianceKind[] = ["all", "too_high", "risk", "flagged"];

const KIND_BY_REASON: Partial<Record<LaneReason, Exclude<ComplianceKind, "all">>> = {
  flagged: "flagged",
  levels_too_high: "too_high",
  audit_risk: "risk",
};

export function isComplianceKind(value: string | null): value is ComplianceKind {
  return value !== null && (COMPLIANCE_KINDS as readonly string[]).includes(value);
}

export function kindOf(row: ComplianceRow): Exclude<ComplianceKind, "all"> | null {
  return row.lane_reason ? (KIND_BY_REASON[row.lane_reason] ?? null) : null;
}

export function inKind(row: ComplianceRow, kind: ComplianceKind): boolean {
  return kind === "all" || kindOf(row) === kind;
}

export function countByKind(rows: ComplianceRow[]): Record<ComplianceKind, number> {
  const counts: Record<ComplianceKind, number> = { all: rows.length, too_high: 0, risk: 0, flagged: 0 };
  for (const row of rows) {
    const kind = kindOf(row);
    if (kind) counts[kind] += 1;
  }
  return counts;
}

export interface CaseFacts {
  billed: string | null;
  supported: string | null;
  inTheNote: string[];
  flagReason: string | null;
  flaggedBy: string | null;
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

export function caseFacts(note: NoteDetail, row: ComplianceRow): CaseFacts {
  const em = note.findings.find((finding) => finding.kind === "em");
  const reasons = em ? mdmReasons(em.detail) : [];
  return {
    billed: em?.code_before ?? null,
    supported: em?.code_after ?? null,
    inTheNote: reasons.length > 0 ? reasons : (em?.evidence ?? []),
    flagReason: row.flag_reason,
    flaggedBy: row.flagged_by_name,
    risks: note.findings
      .filter((finding) => finding.kind === "audit_risk")
      .map((finding) => ({ severity: finding.severity, title: finding.title })),
  };
}
