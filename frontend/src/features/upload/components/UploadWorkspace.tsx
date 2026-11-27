"use client";

import { useState } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import type { Place, Provider, UploadPlan, UploadResult } from "@/lib/api/types";
import { uploadNotes } from "@/lib/api/uploads";
import { VISIT_TYPES } from "@/lib/labels";
import { UPLOAD_TEXT } from "../strings";
import { canStartUpload, includedEntries, makeUploadForm, suggestedServiceDate } from "../uploadEntries";
import { useUploadEntries } from "../useUploadEntries";
import { EmptyDrop } from "./FilePicker";
import { FileTable } from "./FileTable";
import { PlanPanel } from "./PlanPanel";
import { UploadBar } from "./UploadBar";
import { UploadDone } from "./UploadDone";

const EMPTY_PLAN: UploadPlan = { provider_id: "", service_date: "", place_code: "", visit_type: VISIT_TYPES[0] };

interface UploadWorkspaceProps {
  providers: Provider[];
  places: Place[];
  onUploaded: () => void;
}

export function UploadWorkspace({ providers, places, onUploaded }: UploadWorkspaceProps) {
  const [plan, setPlan] = useState<UploadPlan>(EMPTY_PLAN);
  const [result, setResult] = useState<UploadResult | null>(null);
  const files = useUploadEntries();
  const upload = useAction((form: FormData) => uploadNotes(form));
  const included = includedEntries(files.entries);

  async function addFiles(chosen: File[]): Promise<void> {
    const previews = await files.addFiles(chosen);
    const suggested = previews ? suggestedServiceDate(previews) : null;
    if (suggested) setPlan((current) => (current.service_date ? current : { ...current, service_date: suggested }));
  }

  async function start(): Promise<void> {
    const outcome = await upload.run(makeUploadForm(plan, files.entries));
    if (!outcome.ok) return;
    setResult(outcome.value);
    onUploaded();
  }

  function more(): void {
    files.reset();
    upload.clearError();
    setResult(null);
  }

  if (result) return <UploadDone result={result} onMore={more} />;

  const onFiles = (chosen: File[]) => void addFiles(chosen);
  return (
    <>
      <PlanPanel plan={plan} providers={providers} places={places} onChange={setPlan} />
      {files.skipped.length > 0 ? <InlineAlert tone="warn">{UPLOAD_TEXT.files.onlyPdf(files.skipped.join(", "))}</InlineAlert> : null}
      {files.previewError ? <InlineAlert tone="warn">{UPLOAD_TEXT.files.previewFailed}</InlineAlert> : null}
      {files.entries.length === 0 ? (
        <EmptyDrop onFiles={onFiles} />
      ) : (
        <FileTable entries={files.entries} onFiles={onFiles} onUpdate={files.update} onRemove={files.remove} />
      )}
      {files.entries.length > 0 ? (
        <UploadBar
          count={included.length}
          canStart={canStartUpload(plan, files.entries)}
          pending={upload.pending}
          error={upload.error}
          onStart={() => void start()}
        />
      ) : null}
    </>
  );
}
