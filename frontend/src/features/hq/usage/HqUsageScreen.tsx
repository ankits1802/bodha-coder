"use client";

import { UsageFiguresView, hasUsage } from "@/components/shared/usage-figures/UsageFiguresView";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import type { InsightDays } from "@/lib/api/types";
import { getHqUsage } from "@/lib/api/usage";
import { formatCount } from "@/lib/format";
import { INSIGHT_DAYS, parseDays } from "@/lib/insightPeriods";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.usage;
const DEFAULT_DAYS: InsightDays = 14;
const REMOTE_TEXT = { loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry };
const SEGMENTS = INSIGHT_DAYS.map((days) => ({ value: String(days), label: words.periods[days] }));

export function HqUsageScreen() {
  const params = useQueryParams();
  const days = parseDays(params.get("days"), DEFAULT_DAYS);
  const figures = useRemote(`hq-usage:${days}`, () => getHqUsage(days));
  const period = (
    <SegmentedControl
      label={words.periodLabel}
      value={String(days)}
      segments={SEGMENTS}
      onChange={(value) => params.update({ days: Number(value) === DEFAULT_DAYS ? null : value })}
    />
  );
  return (
    <>
      <PageHeader title={words.title} actions={period} />
      <RemoteView state={figures.state} text={REMOTE_TEXT} isEmpty={(data) => !hasUsage(data)} onRetry={figures.reload}>
        {(data) => (
          <>
            <StatGrid label={words.totalsLabel}>
              <StatCell label={words.practices} value={formatCount(data.practices)} />
            </StatGrid>
            <UsageFiguresView figures={data} />
          </>
        )}
      </RemoteView>
    </>
  );
}
