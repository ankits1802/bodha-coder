"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { TextArea } from "@/components/ui/Input";
import { Panel } from "@/components/ui/Panel";
import { RadioOption } from "@/components/ui/RadioOption";
import type { LevelAnswer, LevelChangeBody, LevelChangeView } from "@/lib/api/types";
import { RESPOND_TEXT } from "./strings";

const ANSWERS: readonly LevelAnswer[] = ["confirm", "disagree"];

interface LevelChangeFormProps {
  change: LevelChangeView;
  attestation: string;
  pending: boolean;
  error: string | null;
  onSend: (body: LevelChangeBody) => void;
}

export function levelReply(answer: LevelAnswer | null, comment: string, confirmed: boolean, attestation: string): LevelChangeBody | null {
  const said = comment.trim();
  if (answer === null || !confirmed || (answer === "disagree" && said === "")) return null;
  return { answer, comment: said === "" ? null : said, confirmed, attestation };
}

export function LevelChangeForm({ change, attestation, pending, error, onSend }: LevelChangeFormProps) {
  const name = useId();
  const [answer, setAnswer] = useState<LevelAnswer | null>(null);
  const [comment, setComment] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const reply = levelReply(answer, comment, confirmed, attestation);
  const missingComment = answer === "disagree" && comment.trim() === "";

  return (
    <Panel aria-label={RESPOND_TEXT.levelLabel} className="flex flex-col gap-4 px-5 py-4.5">
      <p className="m-0 text-body-lg whitespace-pre-line">{change.shown}</p>
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="mb-1 p-0 text-subhead font-semibold">{RESPOND_TEXT.levelAnswer}</legend>
        {ANSWERS.map((option) => (
          <RadioOption key={option} name={name} value={option} checked={answer === option} onSelect={() => setAnswer(option)}>
            {RESPOND_TEXT.levelAnswers[option]}
          </RadioOption>
        ))}
      </fieldset>
      <Field
        label={RESPOND_TEXT.levelComment}
        optional={answer === "disagree" ? undefined : RESPOND_TEXT.optional}
        error={missingComment ? RESPOND_TEXT.levelCommentRequired : null}
      >
        {(control) => <TextArea {...control} required={answer === "disagree"} value={comment} onChange={(event) => setComment(event.target.value)} />}
      </Field>
      <label className="flex cursor-pointer items-center gap-3 text-body">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="size-5 flex-none accent-label" />
        {attestation}
      </label>
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button variant="primary" size="lg" className="w-full" disabled={reply === null} pending={pending} onClick={() => reply && onSend(reply)}>
        {RESPOND_TEXT.levelSend}
      </Button>
    </Panel>
  );
}
