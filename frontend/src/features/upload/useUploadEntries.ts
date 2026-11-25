"use client";

import { useRef, useState } from "react";
import { useAction } from "@/hooks/useAction";
import type { FilePreview } from "@/lib/api/types";
import { previewFiles } from "@/lib/api/uploads";
import { applyPreview, isPdf, newEntry, withDuplicates, type UploadEntry } from "./uploadEntries";

export interface UploadEntries {
  entries: UploadEntry[];
  skipped: string[];
  previewError: string | null;
  addFiles: (files: File[]) => Promise<FilePreview[] | null>;
  update: (id: string, change: Partial<Pick<UploadEntry, "billed" | "visitType" | "keep">>) => void;
  remove: (id: string) => void;
  reset: () => void;
}

export function useUploadEntries(): UploadEntries {
  const [entries, setEntries] = useState<UploadEntry[]>([]);
  const [skipped, setSkipped] = useState<string[]>([]);
  const sequence = useRef(0);
  const preview = useAction(previewFiles);

  async function addFiles(files: File[]): Promise<FilePreview[] | null> {
    const pdfs = files.filter(isPdf);
    setSkipped(files.filter((file) => !isPdf(file)).map((file) => file.name));
    if (pdfs.length === 0) return null;
    const added = pdfs.map((file) => {
      sequence.current += 1;
      return newEntry(file, `file-${sequence.current}`);
    });
    setEntries((current) => withDuplicates([...current, ...added]));
    const outcome = await preview.run(pdfs.map((file) => file.name));
    if (!outcome.ok) return null;
    const ids = added.map((entry) => entry.id);
    setEntries((current) => applyPreview(current, ids, outcome.value));
    return outcome.value;
  }

  function update(id: string, change: Partial<Pick<UploadEntry, "billed" | "visitType" | "keep">>): void {
    setEntries((current) => current.map((entry) => (entry.id === id ? { ...entry, ...change } : entry)));
  }

  function remove(id: string): void {
    setEntries((current) => withDuplicates(current.filter((entry) => entry.id !== id)));
  }

  function reset(): void {
    setEntries([]);
    setSkipped([]);
    preview.clearError();
  }

  return { entries, skipped, previewError: preview.error, addFiles, update, remove, reset };
}
