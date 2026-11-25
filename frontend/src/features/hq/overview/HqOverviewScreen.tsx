"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { StatusDot } from "@/components/ui/StatusDot";
import { useRemote } from "@/hooks/useRemote";
import { getHqOverview, getHqPractices } from "@/lib/api/hq";
import type { HqOverview } from "@/lib/api/types";
import { formatCount, formatDay, formatPercent, formatTime, ratio } from "@/lib/format";
import { HQ_TEXT } from "../strings";
import { attentionItems, busiest } from "./overviewModel";
import { AttentionList, BusiestTable, ListSection } from "./PracticeLists";

const words = HQ_TEXT.overview;

function OverviewStats({ overview }: { overview: HqOverview }) {
  const attempts = overview.read_last_24h + overview.failed_last_24h;
  return (
    <StatGrid label={words.statsLabel}>
      <StatCell label={words.read} value={formatCount(overview.read_last_24h)} />
      <StatCell label={words.waiting} value={formatCount(overview.waiting)} />
      <StatCell label={words.running} value={formatCount(overview.running)} />
      <StatCell
        label={words.failed}
        value={formatCount(overview.failed_last_24h)}
        note={words.failedShare(formatPercent(ratio(overview.failed_last_24h, attempts)))}
      />
      <StatCell label={words.tokens} value={formatCount(overview.tokens_last_24h)} />
    </StatGrid>
  );
}

export function HqOverviewScreen() {
  const overview = useRemote("hq-overview", getHqOverview);
  const practices = useRemote("hq-overview-practices", getHqPractices);
  const now = new Date();
  const failed = overview.state.status === "success" ? overview.state.data.failed_last_24h : null;
  const text = { retry: HQ_TEXT.retry, empty: words.empty };

  return (
    <>
      <PageHeader
        title={words.title}
        subtitle={`${formatDay(now, "full")} · ${formatTime(now)}`}
        actions={
          failed === null ? null : (
            <StatusDot tone={failed === 0 ? "ok" : "bad"} className="text-body">
              {failed === 0 ? words.healthy : words.failing(failed)}
            </StatusDot>
          )
        }
      />
      <RemoteView state={overview.state} text={{ ...text, loading: words.loading }} onRetry={overview.reload}>
        {(data) => <OverviewStats overview={data} />}
      </RemoteView>
      <RemoteView state={practices.state} text={{ ...text, loading: HQ_TEXT.practices.loading }} onRetry={practices.reload}>
        {(data) => (
          <div className="flex flex-wrap items-start gap-6">
            <ListSection title={words.attention}>
              <AttentionList items={attentionItems(data)} />
            </ListSection>
            <ListSection title={words.busiest}>
              <BusiestTable practices={busiest(data)} />
            </ListSection>
          </div>
        )}
      </RemoteView>
    </>
  );
}
