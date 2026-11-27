"use client";

import { useEffect, useState } from "react";
import { useRemote, type Remote } from "@/hooks/useRemote";
import { searchNotes } from "@/lib/api/search";
import type { SearchResults } from "@/lib/api/types";

export const MIN_SEARCH_LENGTH = 2;
const DEBOUNCE_MS = 250;

export interface NoteSearch {
  ready: boolean;
  remote: Remote<SearchResults>;
}

function useSettled(value: string): string {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [value]);
  return settled;
}

export function useNoteSearch(text: string): NoteSearch {
  const term = useSettled(text.trim());
  const ready = term.length >= MIN_SEARCH_LENGTH && text.trim().length >= MIN_SEARCH_LENGTH;
  const remote = useRemote(ready ? `search:${term}` : null, () => searchNotes(term));
  return { ready, remote };
}
