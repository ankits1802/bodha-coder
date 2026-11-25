import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { AnalysisView, Finding, NoteDetail } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { AuditChecklist } from "./AuditChecklist";
import { MipsSection } from "./MipsSection";
import { TabSection } from "./TabSection";

const SEVERITY_TONES: Record<string, StatusTone> = { Critical: "bad", High: "bad", Medium: "warn", Low: "neutral" };

function FindingList({ findings }: { findings: Finding[] }) {
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0">
      {findings.map((finding) => (
        <li key={finding.key} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <span className="min-w-0 flex-[1_1_14rem]">
            <span className="font-medium">{finding.title}</span>
            {finding.reasoning ? <span className="block text-callout text-secondary">{finding.reasoning}</span> : null}
          </span>
          {finding.severity ? (
            <StatusDot tone={SEVERITY_TONES[finding.severity] ?? "neutral"}>{REVIEW_TEXT.audit.severity(finding.severity)}</StatusDot>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function AuditSummary({ audit }: { audit: AnalysisView["audit"] }) {
  const words = REVIEW_TEXT.audit;
  const score = audit.overallComplianceScore;
  if (!audit.auditSummary && typeof score !== "number") return null;
  return (
    <TabSection title={words.summary}>
      {typeof score === "number" ? (
        <p className="m-0 text-callout text-secondary">
          {words.score} <span className="font-semibold text-label tabular-nums">{score}</span>
        </p>
      ) : null}
      {audit.auditSummary ? <p className="m-0">{audit.auditSummary}</p> : null}
    </TabSection>
  );
}

function Listed({ title, findings }: { title: string; findings: Finding[] }) {
  if (findings.length === 0) return null;
  return (
    <TabSection title={title}>
      <FindingList findings={findings} />
    </TabSection>
  );
}

export function AuditTab({ detail }: { detail: NoteDetail }) {
  const words = REVIEW_TEXT.audit;
  const audit = detail.analysis?.audit ?? null;
  const byKind = (kind: Finding["kind"]) => detail.findings.filter((item) => item.kind === kind);
  const risks = byKind("audit_risk");
  const notes = byKind("audit_finding");
  const mips = byKind("mips");
  if (!audit && risks.length + notes.length + mips.length === 0) {
    return <p className="m-0 px-5 py-6 text-secondary">{words.none}</p>;
  }
  return (
    <>
      {audit ? <AuditSummary audit={audit} /> : null}
      <Listed title={words.risks} findings={risks} />
      <Listed title={words.findings} findings={notes} />
      {audit ? <AuditChecklist audit={audit} /> : null}
      <MipsSection measures={mips} />
    </>
  );
}
