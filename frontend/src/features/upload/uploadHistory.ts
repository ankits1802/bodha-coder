import { batchCounts } from "@/components/shared/batchProgress";
import type { StatusTone } from "@/components/ui/StatusDot";
import type { UploadedBatch } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { UPLOAD_TEXT } from "./strings";

export interface UploadStatus {
  tone: StatusTone;
  label: string;
}

export function uploadStatus(batch: Pick<UploadedBatch, "counts">): UploadStatus {
  const counts = batchCounts(batch);
  const words = UPLOAD_TEXT.history;
  if (counts.failed > 0) return { tone: "bad", label: words.failed(formatCount(counts.failed)) };
  if (counts.pending > 0) return { tone: "neutral", label: words.reading(formatCount(counts.pending)) };
  return { tone: "ok", label: words.read };
}

export function batchQueueHref(batchId: string): string {
  return `/queue?batch=${encodeURIComponent(batchId)}`;
}
