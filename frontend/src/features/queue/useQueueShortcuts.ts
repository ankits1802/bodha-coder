"use client";

import { useRouter } from "next/navigation";
import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";
import type { QueueRow, User } from "@/lib/api/types";
import { NOTE_ROW_ATTRIBUTE, bulkAbilities, rowToToggle, selectsRows } from "./queueRules";
import type { QueueFilters } from "./useQueueFilters";
import type { QueueSelection } from "./useQueueSelection";

interface QueueShortcutInputs {
  user: User;
  filters: QueueFilters;
  rows: QueueRow[];
  selection: QueueSelection;
  nextHref: string | null;
  onAssign: () => void;
}

function focusedNoteId(): string | null {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement)) return null;
  return active.closest(`[${NOTE_ROW_ATTRIBUTE}]`)?.getAttribute(NOTE_ROW_ATTRIBUTE) ?? null;
}

export function useQueueShortcuts({ user, filters, rows, selection, nextHref, onAssign }: QueueShortcutInputs): void {
  const router = useRouter();
  const selectable = selectsRows(user);
  const selected = rows.filter((row) => selection.selectedIds.includes(row.id));
  const assignable = selected.length > 0 && bulkAbilities(selected, user).assign;

  function toggleRow(): void {
    const noteId = rowToToggle(rows, user, selection.selectedIds, focusedNoteId());
    if (noteId) selection.toggle(noteId);
  }

  useShortcuts("queue", {
    reviewNext: nextHref ? () => router.push(nextHref) : undefined,
    mine: () => filters.update({ assigned: filters.assigned === "me" ? null : "me", offset: null }),
    selectRow: selectable ? toggleRow : undefined,
    assignSelected: selectable && assignable ? onAssign : undefined,
  });
}
