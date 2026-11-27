"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { useRememberedParams } from "@/hooks/useRememberedParams";
import type { User } from "@/lib/api/types";
import { getQueue } from "@/lib/api/work";
import { formatCount } from "@/lib/format";
import { canDo } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { BulkActions, type BulkDialog } from "./components/BulkActions";
import { Pager } from "./components/Pager";
import { QueueFiltersBar } from "./components/QueueFiltersBar";
import { QueueTable } from "./components/QueueTable";
import { QueueViewsBar } from "./components/QueueViewsBar";
import { isApprovable, noteHref, selectsRows } from "./queueRules";
import { QUEUE_TEXT } from "./strings";
import { useQueueActions } from "./useQueueActions";
import { useQueueFilters } from "./useQueueFilters";
import { useQueueSelection } from "./useQueueSelection";
import { useQueueShortcuts } from "./useQueueShortcuts";

const REMOTE_TEXT = { loading: QUEUE_TEXT.loading, empty: QUEUE_TEXT.empty, retry: QUEUE_TEXT.retry };
const REMEMBERED = ["lane", "reason", "assigned", "provider_id", "sort"] as const;

function QueueContent({ user }: { user: User }) {
  const filters = useQueueFilters();
  useRememberedParams("queue", REMEMBERED);
  const queue = useRemote(`queue:${filters.key}`, () => getQueue(filters.query));
  const selection = useQueueSelection(filters.key);
  const [dialog, setDialog] = useState<BulkDialog>(null);
  const actions = useQueueActions(() => {
    selection.select([]);
    queue.reload();
  });
  const page = queue.state.status === "success" ? queue.state.data : null;
  const rows = page?.items ?? [];
  const next = rows.find((row) => row.status === "ready");
  const selectedRows = rows.filter((row) => selection.selectedIds.includes(row.id));
  const controls = {
    lane: filters.lane,
    member: user,
    selectable: selectsRows(user),
    canRemind: canDo(user.role, "ask"),
    remindingId: actions.remindingId,
    onToggle: selection.toggle,
    onRemind: (id: string) => void actions.remindOne(id),
  };
  useQueueShortcuts({
    user,
    filters,
    rows,
    selection,
    nextHref: next ? noteHref(next.id, filters.lane) : null,
    onAssign: () => {
      actions.clearDialogErrors();
      setDialog("assign");
    },
  });
  const failed = page && canDo(user.role, "retry") ? page.failed : 0;
  const approvable = page && filters.lane === "approve" && canDo(user.role, "approve") ? rows.filter(isApprovable) : [];
  const header = (
    <>
      {failed > 0 ? (
        <Button onClick={() => void actions.retryFailed()} pending={actions.retrying}>
          {QUEUE_TEXT.readAgain(formatCount(failed))}
        </Button>
      ) : null}
      {next ? <ButtonLink href={noteHref(next.id, filters.lane)}>{QUEUE_TEXT.reviewNext}</ButtonLink> : null}
      {approvable.length > 0 ? (
        <Button variant="primary" pending={actions.approving} onClick={() => void actions.approveSelected(approvable.map((row) => row.id))}>
          {QUEUE_TEXT.approveAll(formatCount(approvable.length))}
        </Button>
      ) : null}
    </>
  );

  return (
    <>
      <PageHeader title={QUEUE_TEXT.title} subtitle={page ? QUEUE_TEXT.subtitle(formatCount(page.total), filters.sort) : undefined} actions={header} />
      <QueueViewsBar filters={filters} />
      <QueueFiltersBar filters={filters} counts={page} />
      {filters.batchId ? (
        <div className="flex items-center justify-between gap-3 rounded-panel bg-surface px-4 py-2 text-subhead shadow-panel">
          <span>{QUEUE_TEXT.oneBatch}</span>
          <Button size="sm" variant="plain" onClick={() => filters.update({ batch: null, offset: null })}>
            {QUEUE_TEXT.allBatches}
          </Button>
        </div>
      ) : null}
      {actions.notice ? <InlineAlert tone="ok">{actions.notice}</InlineAlert> : null}
      {actions.error ? <InlineAlert tone="bad">{actions.error}</InlineAlert> : null}
      <RemoteView state={queue.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={queue.reload}>
        {(data) => (
          <>
            <QueueTable
              rows={data.items}
              grouped={filters.sort === "due"}
              selectedIds={selection.selectedIds}
              controls={controls}
              onSelectAll={selection.select}
            />
            <Pager
              offset={filters.offset}
              pageSize={data.page_size}
              shown={data.items.length}
              onOffset={(offset) => filters.update({ offset: offset ? String(offset) : null })}
            />
          </>
        )}
      </RemoteView>
      <BulkActions member={user} rows={selectedRows} actions={actions} dialog={dialog} onDialog={setDialog} onClear={() => selection.select([])} />
    </>
  );
}

export function QueueScreen() {
  const { user } = useSession();
  return <AreaGuard area="queue">{user ? <QueueContent user={user} /> : null}</AreaGuard>;
}
