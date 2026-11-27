import type { NoteDetail } from "@/lib/api/types";
import { codeFindings } from "../decisionFlow";
import { codeLabel, latestBilled, quoteCheck } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { BilledCodesEditor } from "./BilledCodesEditor";
import { DecidableRow, type DecisionProps } from "./DecidableRow";
import { ClaimChecksPanel } from "@/components/shared/claim-checks/ClaimChecksPanel";

interface CodesTabProps {
  detail: NoteDetail;
  decision: DecisionProps;
  onSaved: (detail: NoteDetail) => void;
}

export function CodesTab({ detail, decision, onSaved }: CodesTabProps) {
  const findings = codeFindings(detail.findings);
  return (
    <>
      {findings.length === 0 ? <p className="m-0 px-5 py-6 text-secondary">{REVIEW_TEXT.noCodeFindings}</p> : null}
      <ul className="m-0 list-none p-0">
        {findings.map((finding) => (
          <DecidableRow key={finding.key} finding={finding} quote={quoteCheck(finding, detail.texts)} decision={decision} />
        ))}
      </ul>
      <BilledCodesEditor
        noteId={detail.note.id}
        codes={latestBilled(detail.history).map(codeLabel)}
        editable={decision.editable}
        onSaved={onSaved}
      />
      <ClaimChecksPanel noteId={detail.note.id} claim={detail.claim} />
    </>
  );
}
