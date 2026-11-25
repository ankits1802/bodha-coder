import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { CODE_KINDS, codeLabel, latestBilled } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { BilledCodesEditor } from "./BilledCodesEditor";
import { DecisionControl } from "./DecisionControl";
import { FindingRow } from "./FindingRow";

interface CodesTabProps {
  detail: NoteDetail;
  editable: boolean;
  busyKey: string | null;
  onChoose: (finding: Finding, choice: Choice) => void;
  onSaved: (detail: NoteDetail) => void;
}

function kindOrder(finding: Finding): number {
  return CODE_KINDS.indexOf(finding.kind);
}

export function CodesTab({ detail, editable, busyKey, onChoose, onSaved }: CodesTabProps) {
  const findings = detail.findings.filter((item) => CODE_KINDS.includes(item.kind)).sort((a, b) => kindOrder(a) - kindOrder(b));
  return (
    <>
      {findings.length === 0 ? <p className="m-0 px-5 py-6 text-secondary">{REVIEW_TEXT.noCodeFindings}</p> : null}
      <ul className="m-0 list-none p-0">
        {findings.map((finding) => (
          <FindingRow
            key={finding.key}
            finding={finding}
            decision={<DecisionControl finding={finding} editable={editable} busy={busyKey === finding.key} onChoose={onChoose} />}
          />
        ))}
      </ul>
      <BilledCodesEditor
        noteId={detail.note.id}
        codes={latestBilled(detail.history).map(codeLabel)}
        editable={editable}
        onSaved={onSaved}
      />
    </>
  );
}
