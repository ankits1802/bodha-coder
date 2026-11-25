import type { Finding } from "@/lib/api/types";
import type { QuestionDraft } from "../askRequest";
import { REVIEW_TEXT } from "../strings";
import { AskQuestionItem } from "./AskQuestionItem";

interface AskQuestionListProps {
  questions: Finding[];
  drafts: Record<string, QuestionDraft>;
  showErrors: boolean;
  onChange: (key: string, draft: QuestionDraft) => void;
}

export function AskQuestionList({ questions, drafts, showErrors, onChange }: AskQuestionListProps) {
  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className="mb-2 ml-1 text-subhead font-semibold text-secondary">{REVIEW_TEXT.askDialog.questions}</legend>
      <ol className="m-0 list-none overflow-hidden rounded-panel bg-surface p-0 shadow-panel">
        {questions.map((finding, index) => (
          <AskQuestionItem
            key={finding.key}
            index={index + 1}
            finding={finding}
            draft={drafts[finding.key] ?? { include: false, text: "" }}
            showError={showErrors}
            onChange={(draft) => onChange(finding.key, draft)}
          />
        ))}
      </ol>
    </fieldset>
  );
}
