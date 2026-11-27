"use client";

import { useId } from "react";
import { Field } from "@/components/ui/Field";
import { TextArea } from "@/components/ui/Input";
import { RadioOption } from "@/components/ui/RadioOption";
import type { AddendumQuestion } from "@/lib/api/types";
import { needsComment, OTHER_ANSWER, type AnswerDraft } from "./answers";
import { RESPOND_TEXT } from "./strings";

interface QuestionCardProps {
  number: number;
  question: AddendumQuestion;
  draft: AnswerDraft;
  onChange: (draft: AnswerDraft) => void;
}

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
          <RadioOption
            key={option}
            name={name}
            value={option}
            checked={draft.choice === option}
            onSelect={() => onChange({ ...draft, choice: option })}
          >
            {option}
          </RadioOption>
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
