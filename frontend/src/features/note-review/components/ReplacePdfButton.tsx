"use client";

import { useRef, useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { useAction } from "@/hooks/useAction";
import { replaceNoteDocument } from "@/lib/api/notes";
import { isPdfFile } from "../replacePdf";
import { REVIEW_TEXT } from "../strings";

interface ReplacePdfButtonProps {
  noteId: string;
  onReplaced: () => void;
}

export function ReplacePdfButton({ noteId, onReplaced }: ReplacePdfButtonProps) {
  const input = useRef<HTMLInputElement>(null);
  const [chosen, setChosen] = useState<File | null>(null);
  const replace = useAction(replaceNoteDocument);
  const words = REVIEW_TEXT.replacePdf;

  function pick(files: FileList | null): void {
    const file = files?.[0] ?? null;
    if (input.current) input.current.value = "";
    if (!file || !isPdfFile(file)) return;
    replace.clearError();
    setChosen(file);
  }

  async function confirm(): Promise<void> {
    if (!chosen) return;
    const outcome = await replace.run(noteId, chosen);
    if (!outcome.ok) return;
    setChosen(null);
    onReplaced();
  }

  return (
    <>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        aria-label={words.chooseLabel}
        tabIndex={-1}
        className="sr-only"
        onChange={(event) => pick(event.target.files)}
      />
      <Button onClick={() => input.current?.click()}>{words.open}</Button>
      <ConfirmDialog
        open={chosen !== null}
        title={chosen ? words.title(chosen.name) : ""}
        confirmLabel={words.confirm}
        cancelLabel={words.cancel}
        destructive
        pending={replace.pending}
        error={replace.error}
        onConfirm={() => void confirm()}
        onClose={() => setChosen(null)}
      />
    </>
  );
}
