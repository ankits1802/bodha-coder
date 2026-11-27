"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import { UPLOAD_TEXT } from "../strings";

interface FilePickerProps {
  onFiles: (files: File[]) => void;
  label: string;
  variant?: "secondary" | "primary";
}

export function FilePicker({ onFiles, label, variant = "secondary" }: FilePickerProps) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        tabIndex={-1}
        aria-hidden="true"
        className="hidden"
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />
      <Button variant={variant} onClick={() => input.current?.click()}>
        {label}
      </Button>
    </>
  );
}

export function EmptyDrop({ onFiles }: { onFiles: (files: File[]) => void }) {
  const words = UPLOAD_TEXT.files;
  return (
    <section
      aria-label={words.label}
      className="flex flex-col items-center justify-center gap-3 rounded-panel border-2 border-dashed border-separator bg-surface px-6 py-16 text-center"
    >
      <p className="m-0 text-body-lg text-secondary">{words.drop}</p>
      <FilePicker onFiles={onFiles} label={words.choose} />
    </section>
  );
}
