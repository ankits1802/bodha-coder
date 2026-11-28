"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { StatusDot } from "@/components/ui/StatusDot";
import { useRemote } from "@/hooks/useRemote";
import { getHqOverview, getHqPractices } from "@/lib/api/hq";
import type { HqOverview } from "@/lib/api/types";
import { formatCount, formatDay, formatMoney, formatPercent, formatTime, ratio } from "@/lib/format";
import { canReach } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { ORGANIZATIONS_LIST_PATH } from "../organization/organizationTabs";
import { practicesPath } from "../practices/practiceFilters";
import { spendPath } from "../spend/spendModel";
import { HQ_TEXT } from "../strings";
import { attentionItems, busiest } from "./overviewModel";
import { AttentionList, BusiestTable, ListSection } from "./PracticeLists";

const words = HQ_TEXT.overview;

function unpricedNote(count: number): string | undefined {
  return count > 0 ? words.unpriced(count) : undefined;
}

export function OverviewStats({ overview, linked }: { overview: HqOverview; linked: boolean }) {
  const attempts = overview.read_last_24h + overview.failed_last_24h;
  const link = (href: string): string | null => (linked ? href : null);
  return (
    <StatGrid label={words.statsLabel}>
      <StatCell label={words.organizations} value={formatCount(overview.organizations)} href={link(ORGANIZATIONS_LIST_PATH)} />
      <StatCell label={words.practices} value={formatCount(overview.practices)} href={link(practicesPath("live"))} />
      <StatCell label={words.people} value={formatCount(overview.people)} />
      <StatCell label={words.read} value={formatCount(overview.read_last_24h)} />
      <StatCell
        label={words.waiting}
        value={formatCount(overview.waiting)}
        note={words.readingNow(formatCount(overview.running))}
      />
      <StatCell
        label={words.failed}
        value={formatCount(overview.failed_last_24h)}
        note={words.failedShare(formatPercent(ratio(overview.failed_last_24h, attempts)))}
      />
      <StatCell label={words.tokens} value={formatCount(overview.tokens_last_24h)} />
      <StatCell label={words.cost} value={formatMoney(overview.cost_last_24h_usd)} note={unpricedNote(overview.unpriced_last_24h)} />
      <StatCell
        label={words.costThisMonth}
        value={formatMoney(overview.month.cost_usd)}
        note={unpricedNote(overview.month.unpriced_analyses)}
        href={link(spendPath(overview.month))}
      />
    </StatGrid>
  );
}

export function HqOverviewScreen() {
  const { user } = useSession();
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
        {(data) => <OverviewStats overview={data} linked={canReach(user, "hq")} />}
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
