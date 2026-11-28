import type { Finding } from "@/lib/api/types";
import type { MeasureStatus } from "./findings";

export interface PracticeMark {
  key: string;
  version: number;
  identifier: string | null;
}

const REPORTED_AS: Partial<Record<MeasureStatus, string>> = { met: "met", missing: "not-met" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function practiceMark(finding: Finding): PracticeMark | null {
  const mark = finding.detail.practiceMeasure;
  if (!isRecord(mark) || typeof mark.key !== "string" || typeof mark.version !== "number") return null;
  return { key: mark.key, version: mark.version, identifier: typeof mark.identifier === "string" ? mark.identifier : null };
}

export function practiceReportCodes(finding: Finding, status: MeasureStatus | null): string[] {
  const role = status ? REPORTED_AS[status] : undefined;
  const reporting = finding.detail.reportingCodes;
  if (!role || !isRecord(reporting) || !Array.isArray(reporting.codes)) return [];
  return reporting.codes.flatMap((row: unknown) => (isRecord(row) && row.role === role && typeof row.code === "string" ? [row.code] : []));
}
