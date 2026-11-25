import { Button } from "@/components/ui/Button";
import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { openQuestions } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { DecisionControl } from "./DecisionControl";
import { FindingRow } from "./FindingRow";
import { RequestList } from "./RequestList";

interface QuestionsTabProps {
  detail: NoteDetail;
  editable: boolean;
  busyKey: string | null;
  onChoose: (finding: Finding, choice: Choice) => void;
  onAsk: (() => void) | null;
  onRemind: (() => void) | null;
  remindPending: boolean;
  onCancel: (() => void) | null;
  cancelPending: boolean;
  remindMessage: string | null;
}

function isQuestion(finding: Finding): boolean {
  return finding.kind === "cdi_query" || (finding.kind === "diagnosis" && finding.action === "ask");
}

export function QuestionsTab(props: QuestionsTabProps) {
  const { detail, editable, busyKey, onChoose, onAsk, onRemind, remindPending, remindMessage, onCancel, cancelPending } = props;
  const questions = detail.findings.filter(isQuestion);
  const open = openQuestions(detail.findings).length;
  return (
    <>
      {questions.length === 0 ? <p className="m-0 px-5 py-6 text-secondary">{REVIEW_TEXT.questions.none}</p> : null}
      <ul className="m-0 list-none p-0">
        {questions.map((finding) => (
          <FindingRow
            key={finding.key}
            finding={finding}
            decision={<DecisionControl finding={finding} editable={editable} busy={busyKey === finding.key} onChoose={onChoose} />}
          />
        ))}
      </ul>
      {onAsk && open > 0 ? (
        <div className="flex justify-end border-t border-hairline px-5 py-3.5">
          <Button onClick={onAsk}>{REVIEW_TEXT.questions.ask(open)}</Button>
        </div>
      ) : null}
      <RequestList
        requests={detail.requests}
        onRemind={onRemind}
        remindPending={remindPending}
        remindMessage={remindMessage}
        onCancel={onCancel}
        cancelPending={cancelPending}
      />
    </>
  );
}
