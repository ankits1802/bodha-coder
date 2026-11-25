"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { askProvider } from "@/lib/api/notes";
import type { AskBody, Channel, Finding, NoteDetail } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { askBody, initialDrafts, isAskValid, type QuestionDraft } from "../askRequest";
import { REVIEW_TEXT } from "../strings";
import { AskOptions } from "./AskOptions";
import { AskQuestionList } from "./AskQuestionList";

interface AskProviderDialogProps {
  detail: NoteDetail;
  questions: Finding[];
  onClose: () => void;
  onSent: () => void;
}

export function AskProviderDialog({ detail, questions, onClose, onSent }: AskProviderDialogProps) {
  const words = REVIEW_TEXT.askDialog;
  const { note } = detail;
  const formId = useId();
  const [drafts, setDrafts] = useState<Record<string, QuestionDraft>>(() => initialDrafts(questions));
  const [channel, setChannel] = useState<Channel>(note.provider.channel);
  const [hold, setHold] = useState(true);
  const [tried, setTried] = useState(false);
  const send = useAction((body: AskBody) => askProvider(note.id, body));
  const body = askBody(questions, drafts, channel, hold);

  async function submit(): Promise<void> {
    setTried(true);
    if (!isAskValid(body)) return;
    if ((await send.run(body)).ok) onSent();
  }

  const footer = (
    <>
      <Button onClick={onClose}>{words.cancel}</Button>
      <Button type="submit" form={formId} variant="primary" pending={send.pending} disabled={body.questions.length === 0}>
        {words.send(body.questions.length)}
      </Button>
    </>
  );

  return (
    <Dialog
      open
      size="lg"
      onClose={onClose}
      title={words.title(note.provider.name)}
      description={words.about(note.patient_name ?? REVIEW_TEXT.patientUnknown, formatCalendarDay(note.service_date, "long"))}
      footer={footer}
    >
      <form
        id={formId}
        className="flex flex-col gap-5.5"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <AskQuestionList
          questions={questions}
          drafts={drafts}
          showErrors={tried}
          onChange={(key, draft) => setDrafts((current) => ({ ...current, [key]: draft }))}
        />
        <AskOptions channel={channel} onChannel={setChannel} hold={hold} onHold={setHold} />
        {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
