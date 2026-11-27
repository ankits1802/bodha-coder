"use client";

import { useState } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqActivity, getHqPractices } from "@/lib/api/hq";
import { saveFile } from "@/lib/download";
import { HQ_TEXT } from "../strings";
import { ActivityFilters } from "./ActivityFilters";
import { ActivityTable } from "./ActivityTable";
import { activityCsv, matchesSearch } from "./activityModel";

const words = HQ_TEXT.activity;

export function HqActivityScreen() {
  const query = useQueryParams();
  const practiceId = query.get("practice");
  const action = query.get("action");
  const offset = offsetFrom(query.get("offset"));
  const [search, setSearch] = useState(() => query.get("q") ?? "");
  const activity = useRemote(`hq-activity:${practiceId ?? ""}:${action ?? ""}:${offset}`, () =>
    getHqActivity({ practice_id: practiceId, action, offset }),
  );
  const practices = useRemote("hq-activity-practices", getHqPractices);
  const practiceList = practices.state.status === "success" ? practices.state.data : [];
  const names = new Map(practiceList.map((practice) => [practice.id, practice.name]));
  const page = activity.state.status === "success" ? activity.state.data : null;
  const shown = (page?.items ?? []).filter((entry) => matchesSearch(entry, search, names));

  function exportCsv(): void {
    saveFile(new Blob([activityCsv(shown, names)], { type: "text/csv" }), words.fileName);
  }

  return (
    <>
      <PageHeader
        title={words.title}
        actions={
          <Button disabled={shown.length === 0} onClick={exportCsv}>
            {words.export}
          </Button>
        }
      />
      <ActivityFilters
        search={search}
        action={action}
        practiceId={practiceId}
        actions={page?.actions ?? []}
        practices={practiceList}
        onSearch={(value) => {
          setSearch(value);
          query.update({ q: value });
        }}
        onAction={(value) => query.update({ action: value, offset: null })}
        onPractice={(value) => query.update({ practice: value, offset: null })}
      />
      <Panel aria-label={words.tableLabel}>
        <RemoteView
          state={activity.state}
          text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
          isEmpty={(data) => data.offset === 0 && data.items.filter((entry) => matchesSearch(entry, search, names)).length === 0}
          onRetry={activity.reload}
        >
          {() => <ActivityTable entries={shown} names={names} />}
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
