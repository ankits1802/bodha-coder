"use client";

import { useId } from "react";
import { Field } from "@/components/ui/Field";
import { TextArea } from "@/components/ui/Input";
import type { AddendumQuestion } from "@/lib/api/types";
import { needsComment, OTHER_ANSWER, type AnswerDraft } from "./answers";
import { RESPOND_TEXT } from "./strings";

interface QuestionCardProps {
  number: number;
  question: AddendumQuestion;
  draft: AnswerDraft;
  onChange: (draft: AnswerDraft) => void;
}

const OPTION =
  "flex min-h-12 cursor-pointer items-center gap-3 rounded-field px-3.5 text-body text-label shadow-option hover:bg-row-hover has-checked:shadow-option-on has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus";

export function QuestionCard({ number, question, draft, onChange }: QuestionCardProps) {
  const name = useId();
  const other = draft.choice === OTHER_ANSWER;
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 border-t border-hairline px-5 py-4.5 first:border-t-0">
      <legend className="float-left mb-1 w-full p-0 text-body-lg font-semibold">
        {number}. {question.text}
      </legend>
      {question.context.map((quote) => (
        <p key={quote} className="m-0 text-subhead text-secondary">
          {RESPOND_TEXT.quoted(quote)}
        </p>
      ))}
      <div className="mt-1 flex flex-col gap-2">
        {question.options.map((option) => (
          <label key={option} className={OPTION}>
            <input
              type="radio"
              name={name}
              value={option}
              checked={draft.choice === option}
              onChange={() => onChange({ ...draft, choice: option })}
              className="peer sr-only"
            />
            <span
              aria-hidden="true"
              className="size-4.5 flex-none rounded-full border-2 border-chevron bg-surface peer-checked:border-5 peer-checked:border-label"
            />
            {option}
          </label>
        ))}
      </div>
      <Field
        label={other ? RESPOND_TEXT.otherAnswer : RESPOND_TEXT.comment}
        optional={other ? undefined : RESPOND_TEXT.optional}
        error={needsComment(draft) ? RESPOND_TEXT.otherRequired : null}
        className="mt-2"
      >
        {(control) => (
          <TextArea
            {...control}
            required={other}
            value={draft.comment}
            onChange={(event) => onChange({ ...draft, comment: event.target.value })}
          />
        )}
      </Field>
    </fieldset>
  );
}
