"use client";

import { useState } from "react";

export interface QueueSelection {
  selectedIds: string[];
  select: (noteIds: string[]) => void;
  toggle: (noteId: string) => void;
}

export function useQueueSelection(filterKey: string): QueueSelection {
  const [selection, setSelection] = useState<{ key: string; ids: string[] }>({ key: filterKey, ids: [] });
  const selectedIds = selection.key === filterKey ? selection.ids : [];
  const select = (noteIds: string[]) => setSelection({ key: filterKey, ids: noteIds });
  const toggle = (noteId: string) =>
    select(selectedIds.includes(noteId) ? selectedIds.filter((id) => id !== noteId) : [...selectedIds, noteId]);
  return { selectedIds, select, toggle };
}
