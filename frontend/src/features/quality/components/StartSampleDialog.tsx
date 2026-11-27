"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { useRemote } from "@/hooks/useRemote";
import { getQualityOptions, startSample } from "@/lib/api/quality";
import { firstDraft, sampleInput, type SampleDraft } from "../sampleDraft";
import { QUALITY_TEXT } from "../strings";
import { SampleFields } from "./SampleFields";

const FORM_ID = "start-sample-form";
const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noReviewers, retry: QUALITY_TEXT.retry };

interface StartSampleDialogProps {
  onClose: () => void;
  onStarted: (sampleId: string) => void;
}

export function StartSampleDialog({ onClose, onStarted }: StartSampleDialogProps) {
  const today = usePracticeToday();
  const options = useRemote("quality-options", getQualityOptions);
  const [draft, setDraft] = useState<SampleDraft>(() => firstDraft(today));
  const start = useAction(startSample);
  const input = sampleInput(draft);
  const words = QUALITY_TEXT.dialog;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!input) return;
    const outcome = await start.run(input);
    if (outcome.ok) onStarted(outcome.value.id);
  }

  const footer = (
    <>
      <Button onClick={onClose} disabled={start.pending}>
        {words.cancel}
      </Button>
      <Button type="submit" form={FORM_ID} variant="primary" pending={start.pending} disabled={!input}>
        {words.submit}
      </Button>
    </>
  );
  return (
    <Dialog open onClose={onClose} title={words.title} footer={footer} size="lg">
      <RemoteView
        state={options.state}
        text={REMOTE_TEXT}
        isEmpty={(data) => data.reviewers.length === 0}
        onRetry={options.reload}
      >
        {(data) => (
          <form id={FORM_ID} onSubmit={(event) => void submit(event)} className="flex flex-col gap-5">
            <SampleFields draft={draft} options={data} onChange={setDraft} />
            {start.error ? <InlineAlert tone="bad">{start.error}</InlineAlert> : null}
          </form>
        )}
      </RemoteView>
    </Dialog>
  );
}
