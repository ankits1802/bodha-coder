"use client";

import { useQueryParams, type QueryChanges } from "@/hooks/useQueryParams";
import type { Lane, LaneReason, QueueQuery, QueueSort } from "@/lib/api/types";
import { isLane, isLaneReason } from "./queueRules";

export type AssignedFilter = "" | "me" | "none";

export interface QueueFilters {
  lane: Lane | undefined;
  reason: LaneReason | undefined;
  search: string;
  providerId: string;
  batchId: string;
  assigned: AssignedFilter;
  overdue: boolean;
  sort: QueueSort;
  offset: number;
  query: QueueQuery;
  key: string;
  update: (changes: QueryChanges) => void;
}

const OVERDUE_VALUES = ["1", "true"];
const IMPACT: QueueSort = "impact";

function assignedFrom(text: string | null): AssignedFilter {
  return text === "me" || text === "none" ? text : "";
}

function offsetFrom(text: string | null): number {
  const value = Number(text ?? "0");
  return Number.isInteger(value) && value > 0 ? value : 0;
}

export function useQueueFilters(): QueueFilters {
  const params = useQueryParams();
  const laneParam = params.get("lane");
  const reasonParam = params.get("reason");
  const lane = isLane(laneParam) ? laneParam : undefined;
  const reason = isLaneReason(reasonParam) ? reasonParam : undefined;
  const search = params.get("search") ?? "";
  const providerId = params.get("provider_id") ?? "";
  const batchId = params.get("batch") ?? "";
  const assigned = assignedFrom(params.get("assigned"));
  const overdue = OVERDUE_VALUES.includes(params.get("overdue") ?? "");
  const sort: QueueSort = params.get("sort") === IMPACT ? IMPACT : "due";
  const offset = offsetFrom(params.get("offset"));
  const query: QueueQuery = {
    lane,
    reason,
    search: search || undefined,
    provider_id: providerId || undefined,
    batch_id: batchId || undefined,
    assigned: assigned || undefined,
    overdue: overdue || undefined,
    sort: sort === IMPACT ? IMPACT : undefined,
    offset: offset || undefined,
  };
  return {
    lane,
    reason,
    search,
    providerId,
    batchId,
    assigned,
    overdue,
    sort,
    offset,
    query,
    key: JSON.stringify(query),
    update: params.update,
  };
}
