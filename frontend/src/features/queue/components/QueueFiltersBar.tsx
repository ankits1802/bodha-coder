"use client";

import { LOOKUP_SECONDS } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import { getProviders } from "@/lib/api/uploads";
import type { QueueFilters } from "../useQueueFilters";
import { QueueToolbar, type QueueCounts } from "./QueueToolbar";

interface QueueFiltersBarProps {
  filters: QueueFilters;
  counts: QueueCounts | null;
}

export function QueueFiltersBar({ filters, counts }: QueueFiltersBarProps) {
  const providers = useRemote("queue-providers", getProviders, LOOKUP_SECONDS);
  return <QueueToolbar filters={filters} counts={counts} providers={providers.state.status === "success" ? providers.state.data : []} />;
}
