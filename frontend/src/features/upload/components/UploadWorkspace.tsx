"use client";

import { useState } from "react";
import { useDroppedFiles } from "@/components/shared/upload-drop/droppedFiles";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import type { UploadResult } from "@/lib/api/types";
import { uploadNotes } from "@/lib/api/uploads";
import { VISIT_TYPES } from "@/lib/labels";
import { UPLOAD_TEXT } from "../strings";
import { canStartUpload, includedEntries, makeUploadForm, type References } from "../uploadEntries";
import { useUploadEntries } from "../useUploadEntries";
import { DropZone } from "./FilePicker";
import { FileTable } from "./FileTable";
import { PlanPanel } from "./PlanPanel";
import { UploadBar } from "./UploadBar";
import { UploadDone } from "./UploadDone";

interface UploadWorkspaceProps {
  references: References;
  onUploaded: () => void;
}

export function UploadWorkspace({ references, onUploaded }: UploadWorkspaceProps) {
  const [visitType, setVisitType] = useState<string>(VISIT_TYPES[0]);
  const [result, setResult] = useState<UploadResult | null>(null);
  const files = useUploadEntries(references);
  const upload = useAction((form: FormData) => uploadNotes(form));
  const included = includedEntries(files.entries);

  function more(): void {
    files.reset();
    upload.clearError();
    setResult(null);
  }

  function addFiles(chosen: File[]): void {
    if (result) more();
    void files.addFiles(chosen);
  }

  useDroppedFiles(addFiles);

  async function start(): Promise<void> {
    const outcome = await upload.run(makeUploadForm(visitType, files.entries));
    if (!outcome.ok) return;
    setResult(outcome.value);
    onUploaded();
  }

  if (result) return <UploadDone result={result} onMore={more} />;

  if (files.entries.length === 0) {
    return (
      <>
        {files.skipped.length > 0 ? <InlineAlert tone="warn">{UPLOAD_TEXT.files.onlyPdf(files.skipped.join(", "))}</InlineAlert> : null}
        <DropZone onFiles={addFiles} />
      </>
    );
  }

  return (
    <>
      <PlanPanel
        entries={files.entries}
        references={references}
        visitType={visitType}
        onPlace={files.placeAll}
        onPayer={files.choosePayerAll}
        onVisitType={setVisitType}
      />
      {files.skipped.length > 0 ? <InlineAlert tone="warn">{UPLOAD_TEXT.files.onlyPdf(files.skipped.join(", "))}</InlineAlert> : null}
      {files.previewError ? <InlineAlert tone="warn">{UPLOAD_TEXT.files.previewFailed}</InlineAlert> : null}
      <FileTable
        entries={files.entries}
        references={references}
        previewing={files.previewing}
        onUpdate={files.update}
        onPlace={files.place}
        onPayer={files.choosePayer}
        onConfirm={files.confirm}
        onRemove={files.remove}
      />
      <DropZone onFiles={addFiles} compact />
      <UploadBar
        count={included.length}
        canStart={canStartUpload(files.entries) && !files.previewing}
        pending={upload.pending}
        error={upload.error}
        onStart={() => void start()}
      />
    </>
  );
}
