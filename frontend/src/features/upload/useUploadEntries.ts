"use client";

import { useRef, useState } from "react";
import { useAction } from "@/hooks/useAction";
import { previewFiles } from "@/lib/api/uploads";
import {
  applyPreview,
  isPdf,
  newEntry,
  placed,
  withDuplicates,
  type EntryEdit,
  type Placement,
  type References,
  type UploadEntry,
} from "./uploadEntries";

export interface UploadEntries {
  entries: UploadEntry[];
  skipped: string[];
  previewing: boolean;
  previewError: string | null;
  addFiles: (files: File[]) => Promise<void>;
  update: (id: string, change: EntryEdit) => void;
  place: (id: string, change: Partial<Placement>) => void;
  placeAll: (change: Partial<Placement>) => void;
  confirm: (id: string) => void;
  remove: (id: string) => void;
  reset: () => void;
}

export function useUploadEntries(references: References): UploadEntries {
  const [entries, setEntries] = useState<UploadEntry[]>([]);
  const [skipped, setSkipped] = useState<string[]>([]);
  const sequence = useRef(0);
  const preview = useAction(previewFiles);

  async function addFiles(files: File[]): Promise<void> {
    const pdfs = files.filter(isPdf);
    setSkipped(files.filter((file) => !isPdf(file)).map((file) => file.name));
    if (pdfs.length === 0) return;
    const added = pdfs.map((file) => {
      sequence.current += 1;
      return newEntry(file, `file-${sequence.current}`);
    });
    setEntries((current) => withDuplicates([...current, ...added]));
    const outcome = await preview.run(pdfs);
    if (!outcome.ok) return;
    const ids = added.map((entry) => entry.id);
    setEntries((current) => applyPreview(current, ids, outcome.value));
  }

  function edit(id: string, change: (entry: UploadEntry) => UploadEntry): void {
    setEntries((current) => current.map((entry) => (entry.id === id ? change(entry) : entry)));
  }

  function remove(id: string): void {
    setEntries((current) => withDuplicates(current.filter((entry) => entry.id !== id)));
  }

  function reset(): void {
    setEntries([]);
    setSkipped([]);
    preview.clearError();
  }

  return {
    entries,
    skipped,
    previewing: preview.pending,
    previewError: preview.error,
    addFiles,
    update: (id, change) => edit(id, (entry) => ({ ...entry, ...change })),
    place: (id, change) => edit(id, (entry) => placed(entry, change, references)),
    placeAll: (change) => setEntries((current) => current.map((entry) => placed(entry, change, references))),
    confirm: (id) => edit(id, (entry) => ({ ...entry, check: false })),
    remove,
    reset,
  };
}
