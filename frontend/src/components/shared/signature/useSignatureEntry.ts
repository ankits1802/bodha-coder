"use client";

import { useState } from "react";
import type { SignatureEntry } from "./signatureImage";
import { hasInk } from "./strokes";

export interface SignatureEntryState {
  entry: SignatureEntry;
  ready: boolean;
  change: (patch: Partial<SignatureEntry>) => void;
}

export function entryReady(entry: SignatureEntry): boolean {
  if (entry.name.trim() === "") return false;
  if (entry.mode === "drawn") return hasInk(entry.strokes);
  if (entry.mode === "uploaded") return entry.upload !== null;
  return true;
}

export function useSignatureEntry(defaultName: string): SignatureEntryState {
  const [entry, setEntry] = useState<SignatureEntry>({ mode: "drawn", name: defaultName, strokes: [], upload: null });
  return {
    entry,
    ready: entryReady(entry),
    change: (patch) => setEntry((current) => ({ ...current, ...patch })),
  };
}
