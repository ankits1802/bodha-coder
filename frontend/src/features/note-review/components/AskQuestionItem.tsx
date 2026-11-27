import { TextArea } from "@/components/ui/Input";
import type { Finding } from "@/lib/api/types";
import type { QuestionDraft } from "../askRequest";
import { stringList } from "../findings";
import { REVIEW_TEXT } from "../strings";

interface AskQuestionItemProps {
  index: number;
  finding: Finding;
  draft: QuestionDraft;
  showError: boolean;
  onChange: (draft: QuestionDraft) => void;
}

export function AskQuestionItem({ index, finding, draft, showError, onChange }: AskQuestionItemProps) {
  const words = REVIEW_TEXT.askDialog;
  const options = [...new Set([...stringList(finding.detail.options), REVIEW_TEXT.questions.other])];
  const empty = draft.include && draft.text.trim() === "";
  return (
    <li className="flex items-start gap-3 border-t border-hairline px-4 py-3.5 first:border-t-0">
      <input
        type="checkbox"
        checked={draft.include}
        aria-label={words.include(finding.title)}
        onChange={(event) => onChange({ ...draft, include: event.target.checked })}
        className="mt-0.5 size-4.5 flex-none accent-label"
      />
      <span className="flex min-w-0 flex-1 flex-col gap-2">
        <span className="font-semibold">{finding.title}</span>
        <TextArea
          aria-label={words.wording(index)}
          aria-invalid={showError && empty ? true : undefined}
          value={draft.text}
          disabled={!draft.include}
          onChange={(event) => onChange({ ...draft, text: event.target.value })}
          rows={3}
        />
        {showError && empty ? <span className="text-footnote text-bad-text">{words.emptyWording}</span> : null}
        <span className="flex flex-wrap gap-1.5">
          {options.map((option) => (
            <span key={option} className="rounded-full bg-chip px-2.5 py-0.5 text-footnote text-label-soft">
              {option}
            </span>
          ))}
        </span>
      </span>
    </li>
  );
}
