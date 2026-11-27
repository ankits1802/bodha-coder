import { formatMonthYear } from "@/lib/format";
import { Chevron } from "../Chevron";
import { Select } from "../Select";
import { UI_TEXT } from "../strings";
import { canShowEarlier, canShowLater, monthOptions, yearOptions } from "./calendarModel";

interface CalendarHeaderProps {
  year: number;
  month: number;
  today: string;
  min?: string;
  max?: string;
  headingId: string;
  onShift: (months: number) => void;
  onJump: (year: number, month: number) => void;
}

const STEP_BUTTON =
  "flex size-7.5 flex-none cursor-pointer items-center justify-center rounded-full text-secondary hover:bg-fill-plain-hover disabled:cursor-not-allowed disabled:text-quaternary disabled:hover:bg-transparent";

export function CalendarHeader({ year, month, today, min, max, headingId, onShift, onJump }: CalendarHeaderProps) {
  const words = UI_TEXT.date;
  return (
    <div className="flex items-center gap-1 pb-1.5">
      <h2 id={headingId} aria-live="polite" className="sr-only">
        {formatMonthYear(year, month)}
      </h2>
      <button type="button" aria-label={words.previousMonth} disabled={!canShowEarlier(year, month, min)} onClick={() => onShift(-1)} className={STEP_BUTTON}>
        <Chevron direction="left" className="h-3 w-2" />
      </button>
      <div className="flex min-w-0 flex-1 justify-center">
        <Select
          variant="inline"
          label={words.month}
          value={String(month)}
          options={monthOptions(year, min, max)}
          onChange={(next) => onJump(year, Number(next))}
          className="font-semibold"
        />
        <Select
          variant="inline"
          label={words.year}
          value={String(year)}
          options={yearOptions(year, today, min, max)}
          onChange={(next) => onJump(Number(next), month)}
          className="font-semibold tabular-nums"
        />
      </div>
      <button type="button" aria-label={words.nextMonth} disabled={!canShowLater(year, month, max)} onClick={() => onShift(1)} className={STEP_BUTTON}>
        <Chevron direction="right" className="h-3 w-2" />
      </button>
    </div>
  );
}
