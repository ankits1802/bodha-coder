import { Button } from "@/components/ui/Button";
import type { NoteDetail } from "@/lib/api/types";
import { questionFindings } from "../decisionFlow";
import { openQuestions } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { DecidableRow, type DecisionProps } from "./DecidableRow";
import { RequestList } from "./RequestList";

interface QuestionsTabProps {
  detail: NoteDetail;
  decision: DecisionProps;
  onAsk: (() => void) | null;
  onRemind: (() => void) | null;
  remindPending: boolean;
  onCancel: (() => void) | null;
  cancelPending: boolean;
  remindMessage: string | null;
}

export function QuestionsTab(props: QuestionsTabProps) {
  const { detail, decision, onAsk, onRemind, remindPending, remindMessage, onCancel, cancelPending } = props;
  const questions = questionFindings(detail.findings);
  const open = openQuestions(detail.findings).length;
  return (
    <>
      {questions.length === 0 ? <p className="m-0 px-5 py-6 text-secondary">{REVIEW_TEXT.questions.none}</p> : null}
      <ul className="m-0 list-none p-0">
        {questions.map((finding) => (
          <DecidableRow key={finding.key} finding={finding} decision={decision} />
        ))}
      </ul>
      {onAsk && open > 0 ? (
        <div className="flex justify-end border-t border-hairline px-5 py-3.5">
          <Button onClick={onAsk}>{REVIEW_TEXT.questions.ask(open)}</Button>
        </div>
      ) : null}
      <RequestList
        noteId={detail.note.id}
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
