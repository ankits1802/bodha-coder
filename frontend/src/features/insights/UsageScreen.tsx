"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { UsageFiguresView, hasUsage } from "@/components/shared/usage-figures/UsageFiguresView";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getUsageFigures } from "@/lib/api/usage";
import { INSIGHT_DAYS, parseDays } from "@/lib/insightPeriods";
import { useSession } from "@/lib/session/useSession";
import { DEFAULT_DAYS } from "./insightMath";
import { INSIGHTS_TEXT } from "./strings";

const words = INSIGHTS_TEXT.usage;
const REMOTE_TEXT = { loading: words.loading, empty: words.empty, retry: INSIGHTS_TEXT.retry };
const SEGMENTS = INSIGHT_DAYS.map((days) => ({ value: String(days), label: INSIGHTS_TEXT.periods[days] }));

function UsageContent() {
  const params = useQueryParams();
  const days = parseDays(params.get("days"), DEFAULT_DAYS);
  const figures = useRemote(`usage:${days}`, () => getUsageFigures(days));
  const period = (
    <SegmentedControl
      label={INSIGHTS_TEXT.periodLabel}
      value={String(days)}
      segments={SEGMENTS}
      onChange={(value) => params.update({ days: Number(value) === DEFAULT_DAYS ? null : value })}
    />
  );
  return (
    <>
      <PageHeader title={words.title} actions={period} />
      <RemoteView state={figures.state} text={REMOTE_TEXT} isEmpty={(data) => !hasUsage(data)} onRetry={figures.reload}>
        {(data) => <UsageFiguresView figures={data} />}
      </RemoteView>
    </>
  );
}

export function UsageScreen() {
  const { user } = useSession();
  return <AreaGuard area="usage">{user ? <UsageContent /> : null}</AreaGuard>;
}
