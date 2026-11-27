"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqPractices } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { AddPracticeDialog } from "./AddPracticeDialog";
import { EditPracticeDialog } from "./EditPracticeDialog";
import { PlacesPanel } from "./PlacesPanel";
import { PracticeActionDialog } from "./PracticeActionDialog";
import type { PracticeAction } from "./practiceActions";
import { PRACTICE_FILTERS, countPractices, inPracticeFilter, isPracticeFilter, type PracticeFilter } from "./practiceFilters";
import { PracticesTable } from "./PracticesTable";

const words = HQ_TEXT.practices;

export function HqPracticesScreen() {
  const remote = useRemote("hq-practices", getHqPractices);
  const query = useQueryParams();
  const requested = query.get("status");
  const filter: PracticeFilter = isPracticeFilter(requested) ? requested : "all";
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<HqPractice | null>(null);
  const [action, setAction] = useState<PracticeAction | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const list = remote.state.status === "success" ? remote.state.data : null;
  const providerTotal = list ? list.reduce((sum, practice) => sum + practice.providers, 0) : 0;

  function finished(message: string | null): void {
    setAction(null);
    setNotice(message);
    remote.reload();
  }

  return (
    <>
      <PageHeader
        title={words.title}
        subtitle={list ? words.subtitle(list.length, providerTotal) : undefined}
        actions={
          <Button variant="primary" onClick={() => setAdding(true)}>
            {words.add}
          </Button>
        }
      />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      {list ? (
        <SegmentedControl<PracticeFilter>
          label={words.filterLabel}
          value={filter}
          onChange={(next) => query.update({ status: next === "all" ? null : next })}
          segments={PRACTICE_FILTERS.map((value) => ({ value, label: words.filters[value], count: countPractices(list, value) }))}
        />
      ) : null}
      <Panel aria-label={words.tableLabel}>
        <RemoteView
          state={remote.state}
          text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
          isEmpty={(data) => countPractices(data, filter) === 0}
          onRetry={remote.reload}
        >
          {(data) => (
            <PracticesTable
              practices={data.filter((practice) => inPracticeFilter(practice, filter))}
              onEdit={setEditing}
              onAction={(kind, practice) => {
                setNotice(null);
                setAction({ kind, practice });
              }}
            />
          )}
        </RemoteView>
      </Panel>
      <PlacesPanel />
      {adding ? <AddPracticeDialog onClose={() => setAdding(false)} onAdded={() => { setAdding(false); remote.reload(); }} /> : null}
      {editing ? <EditPracticeDialog practice={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); remote.reload(); }} /> : null}
      {action ? <PracticeActionDialog key={`${action.kind}:${action.practice.id}`} action={action} onDone={finished} onClose={() => setAction(null)} /> : null}
    </>
  );
}
