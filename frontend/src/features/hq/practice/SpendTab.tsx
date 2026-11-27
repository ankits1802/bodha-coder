"use client";

import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqExpenditure, type SpendScope } from "@/lib/api/hq";
import { HQ_TEXT } from "../strings";
import { SpendFilters } from "../spend/SpendFilters";
import { rangeFrom, utcToday } from "../spend/spendModel";
import { SpendStats } from "../spend/SpendStats";
import { SpendTable } from "../spend/SpendTable";

const words = HQ_TEXT.spend;

function scopeKey(scope: SpendScope): string {
  return scope.organization_id ? `organization:${scope.organization_id}` : `practice:${scope.practice_id ?? ""}`;
}

export function SpendTab({ scope }: { scope: SpendScope }) {
  const query = useQueryParams();
  const today = utcToday();
  const range = rangeFrom(query.get("from"), query.get("to"), today);
  const spend = useRemote(`hq-scoped-spend:${scopeKey(scope)}:${range.from}:${range.to}`, () => getHqExpenditure(range, scope));
  return (
    <>
      <SpendFilters range={range} today={today} onChange={(next) => query.update({ from: next.from, to: next.to })} />
      <RemoteView
        state={spend.state}
        text={{ loading: words.loading, empty: HQ_TEXT.practice.spendEmpty, retry: HQ_TEXT.retry }}
        isEmpty={(data) => data.practices.length === 0}
        onRetry={spend.reload}
      >
        {(data) => (
          <>
            <SpendStats report={data} />
            <Panel aria-label={words.tableLabel}>
              <SpendTable practices={data.practices} />
            </Panel>
          </>
        )}
      </RemoteView>
    </>
  );
}
