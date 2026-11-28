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

function UploadGlyph({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 15V4" />
      <path d="M7.5 8.5 12 4l4.5 4.5" />
      <path d="M4 14.5V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3.5" />
    </svg>
  );
}

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  compact?: boolean;
}

export function DropZone({ onFiles, compact = false }: DropZoneProps) {
  const words = UPLOAD_TEXT.files;
  const shape = compact ? "flex-row flex-wrap px-5 py-4 gap-4" : "flex-col px-6 py-16 gap-4";
  return (
    <section
      aria-label={compact ? words.addMore : words.label}
      className={`flex items-center justify-center rounded-panel border-2 border-dashed border-separator bg-surface text-center ${shape}`}
    >
      <span className={`flex items-center justify-center rounded-full bg-muted-panel text-secondary ${compact ? "size-9" : "size-14"}`}>
        <UploadGlyph size={compact ? 18 : 28} />
      </span>
      <p className={`m-0 font-medium text-label pointer-coarse:hidden ${compact ? "text-body" : "text-headline"}`}>
        {compact ? words.dropMore : words.drop}
      </p>
      <FilePicker onFiles={onFiles} label={compact ? words.add : words.choose} variant={compact ? "secondary" : "primary"} />
    </section>
  );
}
