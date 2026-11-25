"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import type { QueuePage, Role } from "@/lib/api/types";
import { getQueue } from "@/lib/api/work";
import { formatCount } from "@/lib/format";
import { LANE_ORDER } from "@/lib/labels";
import { canDo } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { BulkBar } from "./components/BulkBar";
import { Pager } from "./components/Pager";
import { QueueFiltersBar } from "./components/QueueFiltersBar";
import { QueueTable } from "./components/QueueTable";
import { noteHref } from "./queueRules";
import { QUEUE_TEXT } from "./strings";
import { useQueueActions } from "./useQueueActions";
import { useQueueFilters } from "./useQueueFilters";
import { useQueueSelection } from "./useQueueSelection";

const REMOTE_TEXT = { loading: QUEUE_TEXT.loading, empty: QUEUE_TEXT.empty, retry: QUEUE_TEXT.retry };

function totalWaiting(page: QueuePage | null): string | undefined {
  if (!page) return undefined;
  return QUEUE_TEXT.subtitle(formatCount(LANE_ORDER.reduce((sum, lane) => sum + page.lanes[lane].total, 0)));
}

function QueueContent({ role }: { role: Role }) {
  const filters = useQueueFilters();
  const queue = useRemote(`queue:${filters.key}`, () => getQueue(filters.query));
  const selection = useQueueSelection(filters.key);
  const actions = useQueueActions(() => {
    selection.select([]);
    queue.reload();
  });
  const page = queue.state.status === "success" ? queue.state.data : null;
  const next = page?.items.find((row) => row.status === "ready");
  const controls = {
    lane: filters.lane,
    selectable: canDo(role, "approve"),
    canRemind: canDo(role, "ask"),
    remindingId: actions.remindingId,
    onToggle: selection.toggle,
    onRemind: (id: string) => void actions.remindOne(id),
  };
  const header = next ? <ButtonLink href={noteHref(next.id, filters.lane)}>{QUEUE_TEXT.reviewNext}</ButtonLink> : null;

  return (
    <>
      <PageHeader title={QUEUE_TEXT.title} subtitle={totalWaiting(page)} actions={header} />
      <QueueFiltersBar filters={filters} lanes={page?.lanes ?? null} />
      {actions.notice ? <InlineAlert tone="ok">{actions.notice}</InlineAlert> : null}
      {actions.error ? <InlineAlert tone="bad">{actions.error}</InlineAlert> : null}
      <RemoteView state={queue.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={queue.reload}>
        {(data) => (
          <>
            <QueueTable rows={data.items} selectedIds={selection.selectedIds} controls={controls} onSelectAll={selection.select} />
            <Pager
              offset={filters.offset}
              pageSize={data.page_size}
              shown={data.items.length}
              onOffset={(offset) => filters.update({ offset: offset ? String(offset) : null })}
            />
          </>
        )}
      </RemoteView>
      <BulkBar
        count={selection.selectedIds.length}
        pending={actions.approving}
        onClear={() => selection.select([])}
        onApprove={() => void actions.approveSelected(selection.selectedIds)}
      />
    </>
  );
}

export function QueueScreen() {
  const { user } = useSession();
  return <AreaGuard area="queue">{user ? <QueueContent role={user.role} /> : null}</AreaGuard>;
}
