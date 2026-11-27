"use client";

import { useEffect } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { announceInboxCount } from "@/components/shared/sidebar/inboxCount";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getInbox, markAllInboxRead, markInboxRead } from "@/lib/api/inbox";
import type { InboxEntry } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { InboxRow } from "./components/InboxRow";
import { isUnread } from "./inboxModel";
import { INBOX_TEXT } from "./strings";

const REMOTE_TEXT = { loading: INBOX_TEXT.loading, empty: INBOX_TEXT.empty, retry: INBOX_TEXT.retry };

function openEntry(entry: InboxEntry): void {
  if (!isUnread(entry)) return;
  markInboxRead([entry.id]).then(
    (count) => announceInboxCount(count.unread),
    () => undefined,
  );
}

function InboxContent() {
  const params = useQueryParams();
  const offset = offsetFrom(params.get("offset"));
  const inbox = useRemote(`inbox:${offset}`, () => getInbox(offset));
  const markAll = useAction(markAllInboxRead);
  const page = inbox.state.status === "success" ? inbox.state.data : null;
  const unread = page?.unread ?? null;

  useEffect(() => {
    if (unread !== null) announceInboxCount(unread);
  }, [unread]);

  async function readAll(): Promise<void> {
    const outcome = await markAll.run();
    if (!outcome.ok) return;
    announceInboxCount(outcome.value.unread);
    inbox.reload();
  }

  return (
    <>
      <PageHeader
        title={INBOX_TEXT.title}
        subtitle={page && page.unread > 0 ? INBOX_TEXT.unreadCount(formatCount(page.unread)) : undefined}
        actions={
          <Button disabled={!page || page.unread === 0} pending={markAll.pending} onClick={() => void readAll()}>
            {INBOX_TEXT.markAllRead}
          </Button>
        }
      />
      {markAll.error ? <InlineAlert tone="bad">{markAll.error}</InlineAlert> : null}
      <RemoteView state={inbox.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0 && data.offset === 0} onRetry={inbox.reload}>
        {(data) => (
          <>
            <Panel as="div">
              <ul aria-label={INBOX_TEXT.listLabel} className="m-0 list-none p-0">
                {data.items.map((entry) => (
                  <InboxRow key={entry.id} entry={entry} onOpen={openEntry} />
                ))}
              </ul>
            </Panel>
            <Pager
              offset={data.offset}
              pageSize={data.page_size}
              shown={data.items.length}
              total={data.total}
              text={SHARED_TEXT.pager}
              onOffset={(next) => params.update({ offset: next > 0 ? String(next) : null })}
            />
          </>
        )}
      </RemoteView>
    </>
  );
}

export function InboxScreen() {
  return (
    <AreaGuard area="inbox">
      <InboxContent />
    </AreaGuard>
  );
}
