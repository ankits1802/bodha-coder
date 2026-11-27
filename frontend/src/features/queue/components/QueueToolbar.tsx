"use client";

import { SegmentedControl, type Segment } from "@/components/ui/SegmentedControl";
import { Select } from "@/components/ui/Select";
import type { Lane, LaneCounts, Provider } from "@/lib/api/types";
import { LANE_LABELS, LANE_ORDER } from "@/lib/labels";
import { QUEUE_TEXT } from "../strings";
import type { AssignedFilter } from "../useQueueFilters";
import { QueueSearch } from "./QueueSearch";

type LaneChoice = Lane | "all";

interface QueueToolbarProps {
  lane: Lane | undefined;
  lanes: LaneCounts | null;
  allTotal: number | undefined;
  search: string;
  providerId: string;
  providers: Provider[];
  assigned: AssignedFilter;
  onLane: (lane: Lane | undefined) => void;
  onSearch: (search: string) => void;
  onProvider: (providerId: string) => void;
  onAssigned: (assigned: string) => void;
}

function laneSegments(lanes: LaneCounts | null, allTotal: number | undefined): Segment<LaneChoice>[] {
  return [
    { value: "all", label: QUEUE_TEXT.all, count: allTotal },
    ...LANE_ORDER.map((lane) => ({ value: lane, label: LANE_LABELS[lane], count: lanes?.[lane].total })),
  ];
}

export function QueueToolbar(props: QueueToolbarProps) {
  const { lane, lanes, allTotal, search, providerId, providers, assigned, onLane, onSearch, onProvider, onAssigned } = props;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2.5">
      <SegmentedControl<LaneChoice>
        label={QUEUE_TEXT.laneFilter}
        value={lane ?? "all"}
        segments={laneSegments(lanes, allTotal)}
        onChange={(choice) => onLane(choice === "all" ? undefined : choice)}
      />
      <div className="flex flex-wrap items-center gap-2">
        <QueueSearch value={search} onSearch={onSearch} />
        <Select
          variant="filter"
          label={QUEUE_TEXT.provider}
          value={providerId}
          options={[{ value: "", label: QUEUE_TEXT.allProviders }, ...providers.map((provider) => ({ value: provider.id, label: provider.name }))]}
          onChange={onProvider}
        />
        <Select
          variant="filter"
          label={QUEUE_TEXT.assignedFilter}
          value={assigned}
          options={[
            { value: "", label: QUEUE_TEXT.anyone },
            { value: "me", label: QUEUE_TEXT.mine },
            { value: "none", label: QUEUE_TEXT.unassigned },
          ]}
          onChange={onAssigned}
        />
      </div>
    </div>
  );
}
