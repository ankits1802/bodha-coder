"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { useQueryParams } from "@/hooks/useQueryParams";
import type { OrganizationInsights } from "@/lib/api/types";
import { formatCount, formatMoneyChange, formatPercent, ratio } from "@/lib/format";
import { InsightTable } from "./InsightTable";
import { ORGANIZATION_TEXT } from "./strings";
import { DEFAULT_DAYS, INSIGHT_DAYS, parseDays, useOrganizationInsights } from "./useOrganizationData";

const words = ORGANIZATION_TEXT.insights;
const TEXT = { loading: words.loading, empty: words.empty, retry: ORGANIZATION_TEXT.retry };
const SEGMENTS = INSIGHT_DAYS.map((days) => ({ value: String(days), label: words.periods[days] }));

function Totals({ insights }: { insights: OrganizationInsights }) {
  const totals = insights.totals;
  const facts = words.facts;
  return (
    <StatGrid label={words.totalsLabel}>
      <StatCell label={facts.notes} value={formatCount(totals.notes)} />
      <StatCell label={facts.approved} value={formatCount(totals.approved)} />
      <StatCell label={facts.onTime} value={formatPercent(ratio(totals.approved_on_time, totals.approved))} />
      <StatCell label={facts.difference} value={formatMoneyChange(totals.difference)} />
    </StatGrid>
  );
}

export function OrganizationInsightsScreen({ organizationId }: { organizationId: string }) {
  const params = useQueryParams();
  const days = parseDays(params.get("days"));
  const remote = useOrganizationInsights(organizationId, days);
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
      <RemoteView state={remote.state} text={TEXT} isEmpty={(data) => data.practices.length === 0} onRetry={remote.reload}>
        {(data) => (
          <>
            <Totals insights={data} />
            <Panel aria-label={words.tableLabel}>
              <InsightTable practices={data.practices} />
            </Panel>
          </>
        )}
      </RemoteView>
    </>
  );
}
