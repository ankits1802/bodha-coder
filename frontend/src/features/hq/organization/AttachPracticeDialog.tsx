"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { RemoteView } from "@/components/ui/RemoteView";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getHqPractices } from "@/lib/api/hq";
import { attachPractice } from "@/lib/api/hqOrganizations";
import type { HqPractice } from "@/lib/api/types";
import { isClosed } from "../practiceStatus";
import { HQ_TEXT } from "../strings";

const FORM_ID = "attach-practice";
const words = HQ_TEXT.organization.practices;

export function unattachedPractices(practices: readonly HqPractice[]): HqPractice[] {
  return practices.filter((practice) => practice.organization_id === null && !isClosed(practice));
}

interface AttachPracticeDialogProps {
  organizationId: string;
  onClose: () => void;
  onAttached: (name: string) => void;
}

function PracticeChoice({ practices, value, onChange }: { practices: HqPractice[]; value: string; onChange: (id: string) => void }) {
  if (practices.length === 0) return <p className="m-0 text-callout text-secondary">{words.attachNone}</p>;
  return (
    <Field label={words.attachChoice}>
      {(control) => (
        <Select
          {...control}
          value={value}
          options={practices.map((practice) => ({ value: practice.id, label: practice.name }))}
          onChange={onChange}
        />
      )}
    </Field>
  );
}

export function AttachPracticeDialog({ organizationId, onClose, onAttached }: AttachPracticeDialogProps) {
  const remote = useRemote("hq-practices", getHqPractices);
  const [chosen, setChosen] = useState<string | null>(null);
  const attach = useAction(attachPractice);
  const choices = remote.state.status === "success" ? unattachedPractices(remote.state.data) : [];
  const selected = choices.find((practice) => practice.id === chosen) ?? choices[0] ?? null;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selected) return;
    const outcome = await attach.run(organizationId, selected.id);
    if (outcome.ok) onAttached(selected.name);
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={words.attachTitle}
      footer={
        <>
          <Button onClick={onClose}>{HQ_TEXT.organization.confirm.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={!selected} pending={attach.pending}>
            {words.attachAction}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
        <RemoteView state={remote.state} text={{ loading: HQ_TEXT.practices.loading, empty: words.attachNone, retry: HQ_TEXT.retry }} onRetry={remote.reload}>
          {() => <PracticeChoice practices={choices} value={selected?.id ?? ""} onChange={setChosen} />}
        </RemoteView>
        {attach.error ? <InlineAlert tone="bad">{attach.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
