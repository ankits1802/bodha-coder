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
import { INSIGHT_DAYS, parseDays } from "@/lib/insightPeriods";
import { useSession } from "@/lib/session/useSession";
import { DailyBars } from "./components/DailyBars";
import { EstimateTable } from "./components/EstimateTable";
import { InsightStats } from "./components/InsightStats";
import { OutcomeBar } from "./components/OutcomeBar";
import { PeopleTable } from "./components/PeopleTable";
import { ProviderTable } from "./components/ProviderTable";
import { DEFAULT_DAYS, dailyBars, isQuiet, rangeStart } from "./insightMath";
import { INSIGHTS_TEXT } from "./strings";
import { EmMixPanel } from "@/components/shared/em-mix/EmMixPanel";
import { QueryMetricsPanel } from "@/components/shared/query-governance/QueryMetricsPanel";

const REMOTE_TEXT = { loading: INSIGHTS_TEXT.loading, empty: INSIGHTS_TEXT.empty, retry: INSIGHTS_TEXT.retry };
const SEGMENTS = INSIGHT_DAYS.map((days) => ({ value: String(days), label: INSIGHTS_TEXT.periods[days] }));

interface InsightsBodyProps {
  insights: Insights;
  days: InsightDays;
  start: string;
  today: string;
}

function InsightsBody({ insights, days, start, today }: InsightsBodyProps) {
  return (
    <>
      <InsightStats insights={insights} />
      <DailyBars bars={dailyBars(insights.per_day, start, today)} />
      <OutcomeBar outcomes={insights.outcomes} />
      <ProviderTable providers={insights.providers} />
      <EstimateTable estimates={insights.estimates} />
      <PeopleTable people={insights.people} />
      <EmMixPanel days={days} />
      <QueryMetricsPanel days={days} />
    </>
  );
}

function InsightsContent() {
  const params = useQueryParams();
  const days: InsightDays = parseDays(params.get("days"), DEFAULT_DAYS);
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
        {(data) => <InsightsBody insights={data} days={days} start={start} today={today} />}
      </RemoteView>
    </>
  );
}

export function InsightsScreen() {
  const { user } = useSession();
  return <AreaGuard area="insights">{user ? <InsightsContent /> : null}</AreaGuard>;
}
