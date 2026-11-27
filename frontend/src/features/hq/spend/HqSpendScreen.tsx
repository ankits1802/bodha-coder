"use client";

import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqExpenditure } from "@/lib/api/hq";
import type { SpendRange } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { formatCalendarDay } from "@/lib/format";
import { HQ_TEXT } from "../strings";
import { SpendFilters } from "./SpendFilters";
import { providerCount, rangeFrom, spendCsv, spendFileName, utcToday } from "./spendModel";
import { SpendStats } from "./SpendStats";
import { SpendTable } from "./SpendTable";

const words = HQ_TEXT.spend;

export const HQ_SPEND_KEY = "hq-spend";

export function HqSpendScreen() {
  const query = useQueryParams();
  const today = utcToday();
  const range = rangeFrom(query.get("from"), query.get("to"), today);
  const spend = useRemote(`${HQ_SPEND_KEY}:${range.from}:${range.to}`, () => getHqExpenditure(range));
  const report = spend.state.status === "success" ? spend.state.data : null;
  const shown = words.range(formatCalendarDay(range.from, "year"), formatCalendarDay(range.to, "year"));

  function download(): void {
    if (report) saveFile(new Blob([spendCsv(report)], { type: "text/csv" }), spendFileName(range));
  }

  function choose(next: SpendRange): void {
    query.update({ from: next.from, to: next.to });
  }

  return (
    <>
      <PageHeader
        title={words.title}
        subtitle={report ? words.zone(shown, report.time_zone) : shown}
        actions={
          <Button disabled={!report || providerCount(report) === 0} onClick={download}>
            {words.download}
          </Button>
        }
      />
      <SpendFilters range={range} today={today} onChange={choose} />
      <RemoteView
        state={spend.state}
        text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
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
