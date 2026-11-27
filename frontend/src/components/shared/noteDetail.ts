"use client";

import { forgetRemote, prefetchRemote } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import { getNote } from "@/lib/api/notes";

const noteKey = (noteId: string): string => `note:${noteId}`;

export function useNoteDetail(noteId: string) {
  return useRemote(noteKey(noteId), () => getNote(noteId));
}

export function prefetchNoteDetail(noteId: string): void {
  prefetchRemote(noteKey(noteId), () => getNote(noteId));
}

export function forgetNoteDetail(noteId: string): void {
  forgetRemote(noteKey(noteId));
}
