"use client";

import { SHARED_TEXT } from "@/components/shared/strings";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqActivity } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { ActivityTable } from "../activity/ActivityTable";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.activity;

export function ActivityTab({ practice }: { practice: HqPractice }) {
  const query = useQueryParams();
  const offset = offsetFrom(query.get("offset"));
  const activity = useRemote(`hq-practice-activity:${practice.id}:${offset}`, () =>
    getHqActivity({ practice_id: practice.id, action: null, offset }),
  );
  const names = new Map([[practice.id, practice.name]]);
  const page = activity.state.status === "success" ? activity.state.data : null;
  return (
    <>
      <Panel aria-label={words.tableLabel}>
        <RemoteView
          state={activity.state}
          text={{ loading: words.loading, empty: HQ_TEXT.practice.activityEmpty, retry: HQ_TEXT.retry }}
          isEmpty={(data) => data.items.length === 0}
          onRetry={activity.reload}
        >
          {(data) => <ActivityTable entries={data.items} names={names} />}
        </RemoteView>
      </Panel>
      {page ? (
        <Pager
          offset={page.offset}
          pageSize={page.page_size}
          shown={page.items.length}
          total={page.total}
          text={SHARED_TEXT.pager}
          onOffset={(next) => query.update({ offset: next > 0 ? String(next) : null })}
        />
      ) : null}
    </>
  );
}
