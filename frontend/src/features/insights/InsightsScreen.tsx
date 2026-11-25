"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { getInsights } from "@/lib/api/billing";
import type { InsightDays, Insights } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { useSession } from "@/lib/session/useSession";
import { DailyBars } from "./components/DailyBars";
import { InsightStats } from "./components/InsightStats";
import { OutcomeBar } from "./components/OutcomeBar";
import { ProviderTable } from "./components/ProviderTable";
import { DEFAULT_DAYS, INSIGHT_DAYS, dailyBars, isQuiet, parseDays, rangeStart } from "./insightMath";
import { INSIGHTS_TEXT } from "./strings";

const REMOTE_TEXT = { loading: INSIGHTS_TEXT.loading, empty: INSIGHTS_TEXT.empty, retry: INSIGHTS_TEXT.retry };
const SEGMENTS = INSIGHT_DAYS.map((days) => ({ value: String(days), label: INSIGHTS_TEXT.periods[days] }));

function InsightsBody({ insights, start, today }: { insights: Insights; start: string; today: string }) {
  return (
    <>
      <InsightStats insights={insights} />
      <DailyBars bars={dailyBars(insights.per_day, start, today)} />
      <OutcomeBar outcomes={insights.outcomes} />
      <ProviderTable providers={insights.providers} />
    </>
  );
}

function InsightsContent() {
  const params = useQueryParams();
  const days: InsightDays = parseDays(params.get("days"));
  const today = usePracticeToday();
  const start = rangeStart(today, days);
  const insights = useRemote(`insights:${days}`, () => getInsights(days));
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
      <PageHeader
        title={INSIGHTS_TEXT.title}
        subtitle={INSIGHTS_TEXT.range(formatCalendarDay(start), formatCalendarDay(today))}
        actions={period}
      />
      <RemoteView state={insights.state} text={REMOTE_TEXT} isEmpty={isQuiet} onRetry={insights.reload}>
        {(data) => <InsightsBody insights={data} start={start} today={today} />}
      </RemoteView>
    </>
  );
}

export function InsightsScreen() {
  const { user } = useSession();
  return <AreaGuard area="insights">{user ? <InsightsContent /> : null}</AreaGuard>;
}
