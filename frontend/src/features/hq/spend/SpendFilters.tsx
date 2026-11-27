import { DateRange } from "@/components/ui/DateRange";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { SpendRange } from "@/lib/api/types";
import { toIsoDate, type CalendarDate } from "@/lib/dates";
import { HQ_TEXT } from "../strings";
import { SPEND_PRESETS, presetOf, presetRange } from "./spendModel";

interface SpendFiltersProps {
  range: SpendRange;
  today: CalendarDate;
  onChange: (range: SpendRange) => void;
}

const words = HQ_TEXT.spend;
const SEGMENTS = SPEND_PRESETS.map((value) => ({ value, label: words.presets[value] }));

export function SpendFilters({ range, today, onChange }: SpendFiltersProps) {
  const todayIso = toIsoDate(today);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <SegmentedControl
        label={words.presetLabel}
        value={presetOf(range, today)}
        segments={SEGMENTS}
        onChange={(preset) => onChange(presetRange(preset, today))}
      />
      <DateRange
        variant="filter"
        start={range.from}
        end={range.to}
        labels={{ start: words.from, end: words.to }}
        max={todayIso}
        today={todayIso}
        onChange={(next) => {
          if (next.start && next.end) onChange({ from: next.start, to: next.end });
        }}
      />
    </div>
  );
}
