"use client";

import { useRemote } from "@/hooks/useRemote";
import type { LaneCounts } from "@/lib/api/types";
import { getProviders } from "@/lib/api/uploads";
import type { QueueFilters } from "../useQueueFilters";
import { QueueToolbar } from "./QueueToolbar";

export function QueueFiltersBar({ filters, lanes }: { filters: QueueFilters; lanes: LaneCounts | null }) {
  const providers = useRemote("queue-providers", getProviders);
  return (
    <QueueToolbar
      lane={filters.lane}
      lanes={lanes}
      search={filters.search}
      providerId={filters.providerId}
      providers={providers.state.status === "success" ? providers.state.data : []}
      onLane={(lane) => filters.update({ lane: lane ?? null, offset: null })}
      onSearch={(search) => filters.update({ search, offset: null })}
      onProvider={(providerId) => filters.update({ provider_id: providerId, offset: null })}
    />
  );
}
