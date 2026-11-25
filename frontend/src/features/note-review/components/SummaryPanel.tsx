import { noteStatus } from "@/components/shared/noteStatus";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import type { Finding, NoteDetail } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { codeChangeCount, highestAuditRisk, openQuestions } from "../findings";
import { REVIEW_TEXT } from "../strings";

function EmHeadline({ em }: { em: Finding }) {
  const { code_before: before, code_after: after } = em;
  if (before && after && before !== after) {
    return (
      <>
        {REVIEW_TEXT.billInstead(after)}
        <span className="text-tertiary line-through">{before}</span>
      </>
    );
  }
  const code = after ?? before;
  return code ? <>{REVIEW_TEXT.billAs(code)}</> : null;
}

function Figure({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="-ml-px flex flex-col gap-0.5 border-l border-hairline px-5.5">
      <dt className="text-caption text-secondary">{label}</dt>
      <dd className="m-0 text-headline font-semibold tracking-headline tabular-nums">{value}</dd>
    </div>
  );
}

function auditRiskLabel(detail: NoteDetail): string {
  if (detail.analysis?.status !== "succeeded") return FORMAT_WORDS.empty;
  return highestAuditRisk(detail.findings) ?? REVIEW_TEXT.kv.none;
}

export function SummaryPanel({ detail }: { detail: NoteDetail }) {
  const status = noteStatus(detail.note);
  const em = detail.findings.find((finding) => finding.kind === "em");
  const score = detail.analysis?.cdi.overallCDIScore;
  const words = REVIEW_TEXT.kv;
  return (
    <Panel aria-label={REVIEW_TEXT.summaryLabel} className="flex flex-wrap items-center justify-between gap-4.5 px-5.5 py-5">
      <div className="flex min-w-0 flex-[999_1_28rem] flex-col gap-1.5">
        <StatusDot tone={status.tone}>{status.label}</StatusDot>
        {em ? (
          <h2 className="m-0 text-title font-semibold tracking-headline">
            <EmHeadline em={em} />
          </h2>
        ) : null}
        {em?.reasoning ? <p className="m-0 max-w-170 text-secondary">{em.reasoning}</p> : null}
      </div>
      <dl className="m-0 flex flex-auto flex-wrap gap-y-3 overflow-hidden">
        <Figure label={words.changes} value={codeChangeCount(detail.findings)} />
        <Figure label={words.questions} value={openQuestions(detail.findings).length} />
        <Figure label={words.auditRisk} value={auditRiskLabel(detail)} />
        <Figure label={words.cdiScore} value={typeof score === "number" ? score : FORMAT_WORDS.empty} />
      </dl>
    </Panel>
  );
}
