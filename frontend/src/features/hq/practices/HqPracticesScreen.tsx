"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useAction } from "@/hooks/useAction";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqPractices, updatePractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { AddPracticeDialog } from "./AddPracticeDialog";
import { EditPracticeDialog } from "./EditPracticeDialog";
import { PlacesPanel } from "./PlacesPanel";
import { PRACTICE_FILTERS, countPractices, inPracticeFilter, isPracticeFilter, type PracticeFilter } from "./practiceFilters";
import { PracticesTable } from "./PracticesTable";

const words = HQ_TEXT.practices;

interface BlockRequest {
  practice: HqPractice;
  block: boolean;
}

function setBlocked({ practice, block }: BlockRequest): Promise<void> {
  return updatePractice(practice.id, { status: block ? "blocked" : "active" });
}

export function HqPracticesScreen() {
  const remote = useRemote("hq-practices", getHqPractices);
  const query = useQueryParams();
  const requested = query.get("status");
  const filter: PracticeFilter = isPracticeFilter(requested) ? requested : "all";
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<HqPractice | null>(null);
  const [blocking, setBlocking] = useState<BlockRequest | null>(null);
  const block = useAction(setBlocked);
  const list = remote.state.status === "success" ? remote.state.data : null;
  const providerTotal = list ? list.reduce((sum, practice) => sum + practice.providers, 0) : 0;

  async function confirmBlock(): Promise<void> {
    if (!blocking) return;
    const outcome = await block.run(blocking);
    if (!outcome.ok) return;
    setBlocking(null);
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
              onBlock={(practice, shouldBlock) => {
                block.clearError();
                setBlocking({ practice, block: shouldBlock });
              }}
            />
          )}
        </RemoteView>
      </Panel>
      <PlacesPanel />
      {adding ? <AddPracticeDialog onClose={() => setAdding(false)} onAdded={() => { setAdding(false); remote.reload(); }} /> : null}
      {editing ? <EditPracticeDialog practice={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); remote.reload(); }} /> : null}
      <ConfirmDialog
        open={blocking !== null}
        title={blocking ? (blocking.block ? words.confirm.block : words.confirm.unblock)(blocking.practice.name) : ""}
        description={blocking?.block ? words.confirm.blockDescription : words.confirm.unblockDescription}
        confirmLabel={blocking?.block ? words.confirm.blockAction : words.confirm.unblockAction}
        cancelLabel={words.confirm.cancel}
        destructive={blocking?.block ?? false}
        pending={block.pending}
        error={block.error}
        onConfirm={() => void confirmBlock()}
        onClose={() => setBlocking(null)}
      />
    </>
  );
}
