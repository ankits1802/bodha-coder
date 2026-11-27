"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import type { Action } from "@/hooks/useAction";
import type { RemittanceUpload } from "@/lib/api/types";
import { REMITTANCE_TEXT } from "../strings";

interface UploadRemittanceButtonProps {
  upload: Action<[File], RemittanceUpload>;
  onUploaded: (result: RemittanceUpload) => void;
}

export function UploadRemittanceButton({ upload, onUploaded }: UploadRemittanceButtonProps) {
  const input = useRef<HTMLInputElement>(null);

  async function pick(files: FileList | null): Promise<void> {
    const file = files?.[0] ?? null;
    if (input.current) input.current.value = "";
    if (!file) return;
    const outcome = await upload.run(file);
    if (outcome.ok) onUploaded(outcome.value);
  }

  return (
    <>
      <input
        ref={input}
        type="file"
        accept=".835,.edi,.txt,.x12"
        aria-label={REMITTANCE_TEXT.uploadLabel}
        tabIndex={-1}
        className="sr-only"
        onChange={(event) => void pick(event.target.files)}
      />
      <Button variant="primary" pending={upload.pending} onClick={() => input.current?.click()}>
        {REMITTANCE_TEXT.upload}
      </Button>
    </>
  );
}
