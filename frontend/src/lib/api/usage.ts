import { request, requestNothing } from "./client";
import type { HqUsageFigures, InsightDays, UsageEvent, UsageFigures } from "./types";

export function sendUsage(events: UsageEvent[], keepalive: boolean): Promise<void> {
  return requestNothing("/api/usage/events", { body: { events }, keepalive });
}

export function getUsageFigures(days: InsightDays): Promise<UsageFigures> {
  return request<UsageFigures>("/api/insights/usage", { query: { days } });
}

export function getHqUsage(days: InsightDays): Promise<HqUsageFigures> {
  return request<HqUsageFigures>("/api/hq/usage", { query: { days } });
}
