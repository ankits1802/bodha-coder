"use client";

import { FilterSelect } from "@/components/ui/FilterSelect";
import { SegmentedControl, type Segment } from "@/components/ui/SegmentedControl";
import type { Lane, LaneCounts, Provider } from "@/lib/api/types";
import { LANE_LABELS, LANE_ORDER } from "@/lib/labels";
import { QUEUE_TEXT } from "../strings";
import { QueueSearch } from "./QueueSearch";

type LaneChoice = Lane | "all";

interface QueueToolbarProps {
  lane: Lane | undefined;
  lanes: LaneCounts | null;
  allTotal: number | undefined;
  search: string;
  providerId: string;
  providers: Provider[];
  onLane: (lane: Lane | undefined) => void;
  onSearch: (search: string) => void;
  onProvider: (providerId: string) => void;
}

function laneSegments(lanes: LaneCounts | null, allTotal: number | undefined): Segment<LaneChoice>[] {
  return [
    { value: "all", label: QUEUE_TEXT.all, count: allTotal },
    ...LANE_ORDER.map((lane) => ({ value: lane, label: LANE_LABELS[lane], count: lanes?.[lane].total })),
  ];
}

export function QueueToolbar(props: QueueToolbarProps) {
  const { lane, lanes, allTotal, search, providerId, providers, onLane, onSearch, onProvider } = props;
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
        <FilterSelect label={QUEUE_TEXT.provider} value={providerId} onChange={(event) => onProvider(event.target.value)}>
          <option value="">{QUEUE_TEXT.allProviders}</option>
          {providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </FilterSelect>
      </div>
    </div>
  );
}
