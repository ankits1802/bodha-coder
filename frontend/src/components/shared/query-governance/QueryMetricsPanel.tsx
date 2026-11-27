"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getQueryMetrics } from "@/lib/api/queryGovernance";
import type { InsightDays } from "@/lib/api/types";
import { QueryMetricsTable } from "./QueryMetricsTable";
import { QUERY_TEXT } from "./strings";

const REMOTE_TEXT = { loading: QUERY_TEXT.loading, empty: QUERY_TEXT.noQueries, retry: QUERY_TEXT.retry };

export function QueryMetricsPanel({ days }: { days: InsightDays }) {
  const metrics = useRemote(`query-metrics:${days}`, () => getQueryMetrics(days));
  return (
    <Panel>
      <PanelHeader title={QUERY_TEXT.title} />
      <RemoteView state={metrics.state} text={REMOTE_TEXT} onRetry={metrics.reload}>
        {(report) => <QueryMetricsTable report={report} />}
      </RemoteView>
    </Panel>
  );
}
