import { request, requestFile, type DownloadedFile } from "./client";
import type { InsightDays, QueryMetricsReport } from "./types";

export function getQueryMetrics(days: InsightDays): Promise<QueryMetricsReport> {
  return request<QueryMetricsReport>("/api/insights/queries", { query: { days } });
}

export function downloadAddendum(noteId: string, requestId: string | null): Promise<DownloadedFile> {
  return requestFile(`/api/notes/${encodeURIComponent(noteId)}/addendum.txt`, { query: { request_id: requestId } });
}
