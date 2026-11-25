import { request } from "./client";
import type { ComplianceList, QueuePage, QueueQuery, TodaySummary } from "./types";

export function getToday(): Promise<TodaySummary> {
  return request<TodaySummary>("/api/today");
}

export function getQueue(query: QueueQuery): Promise<QueuePage> {
  return request<QueuePage>("/api/notes", { query: { ...query } });
}

export function getCompliance(): Promise<ComplianceList> {
  return request<ComplianceList>("/api/compliance");
}
