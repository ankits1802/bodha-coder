"use client";

import { LOOKUP_SECONDS } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import type { LaneCounts } from "@/lib/api/types";
import { getProviders } from "@/lib/api/uploads";
import type { QueueFilters } from "../useQueueFilters";
import { QueueToolbar } from "./QueueToolbar";

interface QueueFiltersBarProps {
  filters: QueueFilters;
  lanes: LaneCounts | null;
  allTotal: number | undefined;
}

export function QueueFiltersBar({ filters, lanes, allTotal }: QueueFiltersBarProps) {
  const providers = useRemote("queue-providers", getProviders, LOOKUP_SECONDS);
  return (
    <QueueToolbar
      lane={filters.lane}
      lanes={lanes}
      allTotal={allTotal}
      search={filters.search}
      providerId={filters.providerId}
      providers={providers.state.status === "success" ? providers.state.data : []}
      assigned={filters.assigned}
      onLane={(lane) => filters.update({ lane: lane ?? null, offset: null })}
      onSearch={(search) => filters.update({ search, offset: null })}
      onProvider={(providerId) => filters.update({ provider_id: providerId, offset: null })}
      onAssigned={(assigned) => filters.update({ assigned, offset: null })}
    />
  );
}
