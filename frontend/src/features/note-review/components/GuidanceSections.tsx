import type { AnalysisView, NoteDetail } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { AuditChecklist } from "./AuditChecklist";
import { MipsSection } from "./MipsSection";
import { ReviewSection } from "./ReviewSection";

function AuditSummary({ audit }: { audit: AnalysisView["audit"] }) {
  const words = REVIEW_TEXT.audit;
  const score = audit.overallComplianceScore;
  if (!audit.auditSummary && typeof score !== "number") return null;
  return (
    <ReviewSection title={words.summary}>
      {typeof score === "number" ? (
        <p className="m-0 text-callout text-secondary">
          {words.score} <span className="font-semibold text-label tabular-nums">{score}</span>
        </p>
      ) : null}
      {audit.auditSummary ? <p className="m-0">{audit.auditSummary}</p> : null}
    </ReviewSection>
  );
}

function hasAudit(audit: AnalysisView["audit"] | undefined): boolean {
  if (!audit) return false;
  const lists = [audit.requiredElements, audit.codingCompliance, audit.cmsCDICompliance];
  return Boolean(audit.auditSummary) || typeof audit.overallComplianceScore === "number" || lists.some((list) => Boolean(list?.length));
}

export function hasGuidance(detail: Pick<NoteDetail, "analysis" | "findings">): boolean {
  const cdi = detail.analysis?.cdi;
  if (cdi?.summaryGuidance || cdi?.codeLinkingOpportunities?.length) return true;
  return hasAudit(detail.analysis?.audit) || detail.findings.some((item) => item.kind === "mips");
}

export function GuidanceSections({ detail }: { detail: NoteDetail }) {
  const words = REVIEW_TEXT.wording;
  const guidance = detail.analysis?.cdi.summaryGuidance ?? null;
  const links = detail.analysis?.cdi.codeLinkingOpportunities ?? [];
  const audit = detail.analysis?.audit ?? null;
  return (
    <>
      {guidance ? (
        <ReviewSection title={words.guidance}>
          <p className="m-0">{guidance}</p>
        </ReviewSection>
      ) : null}
      {links.length > 0 ? (
        <ReviewSection title={words.linking}>
          <ul className="m-0 flex flex-col gap-1.5 pl-4.5">
            {links.map((link) => (
              <li key={`${link.diagnosis}-${link.suggestion}`}>
                <span className="font-medium">{link.diagnosis}</span>
                <span className="block text-callout text-secondary">{link.suggestion}</span>
              </li>
            ))}
          </ul>
        </ReviewSection>
      ) : null}
      {audit ? <AuditSummary audit={audit} /> : null}
      {audit ? <AuditChecklist audit={audit} /> : null}
      <MipsSection measures={detail.findings.filter((item) => item.kind === "mips")} />
    </>
  );
}
