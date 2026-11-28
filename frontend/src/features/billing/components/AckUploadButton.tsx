"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import { useAction } from "@/hooks/useAction";
import { uploadAcknowledgment } from "@/lib/api/claims";
import type { AckUpload } from "@/lib/api/types";
import { CLAIM_FILE_TEXT } from "../strings";

function uploadNotice(result: AckUpload): string {
  if (result.kind === "duplicate") return CLAIM_FILE_TEXT.duplicate;
  return CLAIM_FILE_TEXT.uploaded(result.kind, result.accepted, result.rejected);
}

export function AckUploadButton({ onUploaded }: { onUploaded: (notice: string) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const upload = useAction(uploadAcknowledgment);

  async function pick(files: FileList | null): Promise<void> {
    const file = files?.[0] ?? null;
    if (input.current) input.current.value = "";
    if (!file) return;
    const outcome = await upload.run(file);
    if (outcome.ok) onUploaded(uploadNotice(outcome.value));
  }

  return (
    <>
      <input
        ref={input}
        type="file"
        accept=".txt,.x12,.999,.277,.edi"
        aria-label={CLAIM_FILE_TEXT.uploadLabel}
        tabIndex={-1}
        className="sr-only"
        onChange={(event) => void pick(event.target.files)}
      />
      <Button size="sm" pending={upload.pending} onClick={() => input.current?.click()}>
        {CLAIM_FILE_TEXT.upload}
      </Button>
      {upload.error ? (
        <span role="alert" className="basis-full text-footnote text-bad-text">
          {upload.error}
        </span>
      ) : null}
    </>
  );
}
