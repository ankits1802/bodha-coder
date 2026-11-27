"use client";

import { useRemote, type Remote } from "@/hooks/useRemote";
import { useSettled } from "@/hooks/useSettled";
import { searchNotes } from "@/lib/api/search";
import type { SearchResults } from "@/lib/api/types";

export const MIN_SEARCH_LENGTH = 2;

export interface NoteSearch {
  ready: boolean;
  remote: Remote<SearchResults>;
}

export function useNoteSearch(text: string): NoteSearch {
  const term = useSettled(text.trim());
  const ready = term.length >= MIN_SEARCH_LENGTH && text.trim().length >= MIN_SEARCH_LENGTH;
  const remote = useRemote(ready ? `search:${term}` : null, () => searchNotes(term));
  return { ready, remote };
}
