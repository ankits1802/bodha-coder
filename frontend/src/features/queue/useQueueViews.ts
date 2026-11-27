"use client";

import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import type { QueueViewFilters, QueueViews } from "@/lib/api/types";
import { deleteQueueView, getQueueViews, saveQueueView } from "@/lib/api/work";

export interface QueueViewActions {
  views: QueueViews | null;
  save: (name: string, filters: QueueViewFilters) => Promise<boolean>;
  saving: boolean;
  saveError: string | null;
  clearSaveError: () => void;
  remove: (viewId: string) => Promise<void>;
  removeError: string | null;
}

export function useQueueViews(): QueueViewActions {
  const remote = useRemote("queue-views", getQueueViews);
  const saving = useAction(saveQueueView);
  const removing = useAction(deleteQueueView);

  async function save(name: string, filters: QueueViewFilters): Promise<boolean> {
    const outcome = await saving.run({ name, filters });
    if (outcome.ok) remote.reload();
    return outcome.ok;
  }

  async function remove(viewId: string): Promise<void> {
    const outcome = await removing.run(viewId);
    if (outcome.ok) remote.reload();
  }

  return {
    views: remote.state.status === "success" ? remote.state.data : null,
    save,
    saving: saving.pending,
    saveError: saving.error,
    clearSaveError: saving.clearError,
    remove,
    removeError: removing.error,
  };
}
