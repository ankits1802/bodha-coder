import type { BatchProgress } from "@/lib/api/types";

export interface BatchCounts {
  total: number;
  finished: number;
  pending: number;
  failed: number;
}

export function batchCounts(batch: BatchProgress): BatchCounts {
  const counts = batch.counts;
  const total = Object.values(counts).reduce((sum, value) => sum + (value ?? 0), 0);
  const pending = (counts.queued ?? 0) + (counts.reading ?? 0);
  return { total, finished: total - pending, pending, failed: counts.failed ?? 0 };
}
