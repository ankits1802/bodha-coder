"use client";

import { useQueryParams, type QueryChanges } from "@/hooks/useQueryParams";
import type { Lane, QueueQuery } from "@/lib/api/types";
import { isLane } from "./queueRules";

export interface QueueFilters {
  lane: Lane | undefined;
  search: string;
  providerId: string;
  offset: number;
  query: QueueQuery;
  key: string;
  update: (changes: QueryChanges) => void;
}

function offsetFrom(text: string | null): number {
  const value = Number(text ?? "0");
  return Number.isInteger(value) && value > 0 ? value : 0;
}

export function useQueueFilters(): QueueFilters {
  const params = useQueryParams();
  const laneParam = params.get("lane");
  const lane = isLane(laneParam) ? laneParam : undefined;
  const search = params.get("search") ?? "";
  const providerId = params.get("provider_id") ?? "";
  const offset = offsetFrom(params.get("offset"));
  const query: QueueQuery = {
    lane,
    search: search || undefined,
    provider_id: providerId || undefined,
    offset: offset || undefined,
  };
  return { lane, search, providerId, offset, query, key: JSON.stringify(query), update: params.update };
}
