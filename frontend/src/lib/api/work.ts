import { request, requestNothing } from "./client";
import type { ComplianceList, QueuePage, QueueQuery, QueueViewBody, QueueViews, SavedView, TodaySummary } from "./types";

export function getToday(): Promise<TodaySummary> {
  return request<TodaySummary>("/api/today");
}

export function getQueue(query: QueueQuery): Promise<QueuePage> {
  return request<QueuePage>("/api/notes", { query: { ...query } });
}

export function getCompliance(): Promise<ComplianceList> {
  return request<ComplianceList>("/api/compliance");
}

export function getQueueViews(): Promise<QueueViews> {
  return request<QueueViews>("/api/queue-views");
}

export function saveQueueView(body: QueueViewBody): Promise<SavedView> {
  return request<SavedView>("/api/queue-views", { body });
}

export function deleteQueueView(viewId: string): Promise<void> {
  return requestNothing(`/api/queue-views/${encodeURIComponent(viewId)}`, { method: "DELETE" });
}
