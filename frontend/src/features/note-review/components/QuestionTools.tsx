import { Button } from "@/components/ui/Button";
import type { NoteDetail } from "@/lib/api/types";
import { askableQuestions } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { RequestList } from "./RequestList";

export interface QuestionToolsProps {
  onAsk: (() => void) | null;
  onRemind: (() => void) | null;
  remindPending: boolean;
  onCancel: (() => void) | null;
  cancelPending: boolean;
  remindMessage: string | null;
}

export function hasQuestionTools(detail: NoteDetail, tools: QuestionToolsProps): boolean {
  return tools.onAsk !== null || detail.requests.length > 0;
}

export function QuestionTools({ detail, tools }: { detail: NoteDetail; tools: QuestionToolsProps }) {
  const { onAsk, onRemind, remindPending, remindMessage, onCancel, cancelPending } = tools;
  const askable = askableQuestions(detail.findings, detail.requests).length;
  return (
    <>
      {onAsk && askable > 0 ? (
        <div className="flex justify-end border-t border-hairline px-5 py-3.5">
          <Button onClick={onAsk}>{REVIEW_TEXT.questions.ask(askable)}</Button>
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
