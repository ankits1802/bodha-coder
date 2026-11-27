"use client";

import { SegmentedControl, type Segment } from "@/components/ui/SegmentedControl";
import { Select } from "@/components/ui/Select";
import type { LaneCounts, Provider, ProviderReasonCounts, QueueSort } from "@/lib/api/types";
import { LANE_VIEWS } from "@/lib/labels";
import { laneChanges, laneChoice, type LaneChoice } from "../queueViews";
import { QUEUE_TEXT } from "../strings";
import type { QueueFilters } from "../useQueueFilters";
import { QueueSearch } from "./QueueSearch";

export interface QueueCounts {
  lanes: LaneCounts;
  provider_reasons: ProviderReasonCounts;
  all_total: number;
}

interface QueueToolbarProps {
  filters: QueueFilters;
  counts: QueueCounts | null;
  providers: Provider[];
}

const SORTS: QueueSort[] = ["due", "impact"];

function laneSegments(counts: QueueCounts | null): Segment<LaneChoice>[] {
  return [
    { value: "all", label: QUEUE_TEXT.all, count: counts?.all_total },
    ...LANE_VIEWS.map((view) => ({
      value: view.key,
      label: view.label,
      count: view.reason ? counts?.provider_reasons[view.reason].total : counts?.lanes[view.lane].total,
    })),
  ];
}

export function QueueToolbar({ filters, counts, providers }: QueueToolbarProps) {
  const update = filters.update;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2.5">
      <SegmentedControl<LaneChoice>
        label={QUEUE_TEXT.laneFilter}
        value={laneChoice(filters)}
        segments={laneSegments(counts)}
        onChange={(choice) => update(laneChanges(choice))}
      />
      <div className="flex flex-wrap items-center gap-2">
        <QueueSearch value={filters.search} onSearch={(search) => update({ search, offset: null })} />
        <Select
          variant="filter"
          label={QUEUE_TEXT.provider}
          value={filters.providerId}
          options={[{ value: "", label: QUEUE_TEXT.allProviders }, ...providers.map((provider) => ({ value: provider.id, label: provider.name }))]}
          onChange={(providerId) => update({ provider_id: providerId, offset: null })}
        />
        <Select
          variant="filter"
          label={QUEUE_TEXT.assignedFilter}
          value={filters.assigned}
          options={[
            { value: "", label: QUEUE_TEXT.anyone },
            { value: "me", label: QUEUE_TEXT.mine },
            { value: "none", label: QUEUE_TEXT.unassigned },
          ]}
          onChange={(assigned) => update({ assigned, offset: null })}
        />
        <Select<QueueSort>
          variant="filter"
          label={QUEUE_TEXT.sort}
          value={filters.sort}
          options={SORTS.map((sort) => ({ value: sort, label: QUEUE_TEXT.sorts[sort] }))}
          onChange={(sort) => update({ sort: sort === "impact" ? sort : null, offset: null })}
        />
      </div>
    </div>
  );
}
