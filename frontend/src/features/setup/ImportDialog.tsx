"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { TextArea } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { importProviders } from "@/lib/api/practice";
import { PROVIDER_TEXT } from "./strings";

const FORM_ID = "provider-import";
const FILE_BUTTON =
  "text-subhead text-secondary file:mr-3 file:h-8 file:cursor-pointer file:rounded-full file:border-0 file:bg-fill file:px-4 file:text-body file:font-medium file:text-label";

interface ImportDialogProps {
  onClose: () => void;
  onImported: (count: number) => void;
}

export function ImportDialog({ onClose, onImported }: ImportDialogProps) {
  const [csv, setCsv] = useState("");
  const [missing, setMissing] = useState(false);
  const upload = useAction(importProviders);
  const words = PROVIDER_TEXT.importDialog;

  async function readFile(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    if (!file) return;
    setCsv(await file.text());
    setMissing(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!csv.trim()) {
      setMissing(true);
      return;
    }
    const outcome = await upload.run(csv);
    if (outcome.ok) onImported(outcome.value.imported);
  }

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={words.title}
      footer={
        <>
          <Button onClick={onClose}>{words.cancel}</Button>
          <Button type="submit" form={FORM_ID} variant="primary" pending={upload.pending}>
            {words.submit}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} onSubmit={submit} className="flex flex-col gap-4">
        <Field label={words.csv} hint={words.columns} error={missing ? words.empty : null}>
          {(control) => (
            <TextArea
              {...control}
              rows={8}
              value={csv}
              onChange={(event) => setCsv(event.target.value)}
              className="tabular-nums"
            />
          )}
        </Field>
        <Field label={words.file}>
          {(control) => (
            <input {...control} type="file" accept=".csv,text/csv" onChange={(event) => void readFile(event)} className={FILE_BUTTON} />
          )}
        </Field>
        {upload.error ? <InlineAlert tone="bad">{upload.error}</InlineAlert> : null}
      </form>
    </Dialog>
  );
}
