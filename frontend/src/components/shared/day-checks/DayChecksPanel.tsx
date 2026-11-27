"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getFlaggedDays } from "@/lib/api/defensibility";
import { addDays } from "@/lib/dates";
import { DayChecksList } from "./DayChecksList";
import { DAY_TEXT } from "./strings";

type DayRange = keyof typeof DAY_TEXT.ranges;

const RANGE_PARAM = "day_range";
const DEFAULT_RANGE: DayRange = "30";
const RANGES = Object.keys(DAY_TEXT.ranges) as DayRange[];
const SEGMENTS = RANGES.map((value) => ({ value, label: DAY_TEXT.ranges[value] }));
const REMOTE_TEXT = { loading: DAY_TEXT.loading, empty: DAY_TEXT.empty, retry: DAY_TEXT.retry };

function parseRange(value: string | null): DayRange {
  return RANGES.find((range) => range === value) ?? DEFAULT_RANGE;
}

export function DayChecksPanel() {
  const params = useQueryParams();
  const range = parseRange(params.get(RANGE_PARAM));
  const to = usePracticeToday();
  const from = addDays(to, -(Number(range) - 1)) ?? to;
  const days = useRemote(`flagged-days:${from}:${to}`, () => getFlaggedDays(from, to));
  const control = (
    <SegmentedControl
      label={DAY_TEXT.rangeLabel}
      size="sm"
      value={range}
      segments={SEGMENTS}
      onChange={(value) => params.update({ [RANGE_PARAM]: value === DEFAULT_RANGE ? null : value })}
    />
  );
  return (
    <Panel aria-label={DAY_TEXT.panelTitle}>
      <PanelHeader title={DAY_TEXT.panelTitle} actions={control} />
      <RemoteView state={days.state} text={REMOTE_TEXT} isEmpty={(data) => data.days.length === 0} onRetry={days.reload}>
        {(data) => <DayChecksList days={data.days} />}
      </RemoteView>
    </Panel>
  );
}
