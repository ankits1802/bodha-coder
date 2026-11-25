"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { FilterSelect } from "@/components/ui/FilterSelect";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SearchField } from "@/components/ui/SearchField";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqActivity, getHqPractices } from "@/lib/api/hq";
import { saveFile } from "@/lib/download";
import { HQ_TEXT } from "../strings";
import { ActivityTable } from "./ActivityTable";
import { actionLabel, actionsIn, activityCsv, matchesFilter, type ActivityFilter } from "./activityModel";

const words = HQ_TEXT.activity;

export function HqActivityScreen() {
  const query = useQueryParams();
  const practiceId = query.get("practice");
  const [search, setSearch] = useState(() => query.get("q") ?? "");
  const filter: ActivityFilter = { search, action: query.get("action") };
  const activity = useRemote(`hq-activity:${practiceId ?? ""}`, () => getHqActivity(practiceId));
  const practices = useRemote("hq-activity-practices", getHqPractices);
  const practiceList = practices.state.status === "success" ? practices.state.data : [];
  const names = new Map(practiceList.map((practice) => [practice.id, practice.name]));
  const entries = activity.state.status === "success" ? activity.state.data : [];
  const shown = entries.filter((entry) => matchesFilter(entry, filter, names));

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
      <div className="flex flex-wrap gap-2">
        <SearchField
          label={words.search}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            query.update({ q: event.target.value });
          }}
        />
        <FilterSelect label={words.action} value={filter.action ?? ""} onChange={(event) => query.update({ action: event.target.value })}>
          <option value="">{words.anyAction}</option>
          {actionsIn(entries).map((action) => (
            <option key={action} value={action}>
              {actionLabel(action)}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect label={words.practice} value={practiceId ?? ""} onChange={(event) => query.update({ practice: event.target.value })}>
          <option value="">{words.anyPractice}</option>
          {practiceList.map((practice) => (
            <option key={practice.id} value={practice.id}>
              {practice.name}
            </option>
          ))}
        </FilterSelect>
      </div>
      <Panel aria-label={words.tableLabel}>
        <RemoteView
          state={activity.state}
          text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
          isEmpty={(data) => data.filter((entry) => matchesFilter(entry, filter, names)).length === 0}
          onRetry={activity.reload}
        >
          {() => <ActivityTable entries={shown} names={names} />}
        </RemoteView>
      </Panel>
    </>
  );
}
