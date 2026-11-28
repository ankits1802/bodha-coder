import type { KeyboardEvent, RefObject } from "react";
import { isWithin, monthWeeks } from "@/lib/dates";
import { WEEK_STARTS_ON, WEEKDAY_NAMES, formatCalendarDay } from "@/lib/format";

interface CalendarGridProps {
  year: number;
  month: number;
  focused: string;
  selected: string | null;
  today: string;
  min?: string;
  max?: string;
  labelledBy: string;
  gridRef: RefObject<HTMLTableElement | null>;
  onKey: (event: KeyboardEvent<HTMLButtonElement>) => void;
  onPick: (day: string) => void;
}

const DAY_OF_MONTH = 8;

function dayTone(selected: boolean, today: boolean): string {
  if (selected) return "bg-inverse font-semibold text-on-inverse";
  if (today) return "font-semibold text-label shadow-option-on hover:bg-fill-plain-hover";
  return "text-label hover:bg-fill-plain-hover";
}

export function CalendarGrid({ year, month, focused, selected, today, min, max, labelledBy, gridRef, onKey, onPick }: CalendarGridProps) {
  return (
    <table ref={gridRef} role="grid" aria-labelledby={labelledBy} className="w-full border-collapse">
      <thead>
        <tr>
          {WEEKDAY_NAMES.map((name) => (
            <th key={name.long} scope="col" className="h-7 p-0 text-center text-caption font-medium text-secondary">
              <span aria-hidden="true">{name.narrow}</span>
              <span className="sr-only">{name.long}</span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {monthWeeks(year, month, WEEK_STARTS_ON).map((week, row) => (
          <tr key={row}>
            {week.map((day, column) =>
              day ? (
                <td key={day} role="gridcell" aria-selected={day === selected} className="p-0.5 text-center">
                  <button
                    type="button"
                    tabIndex={day === focused ? 0 : -1}
                    disabled={!isWithin(day, min, max)}
                    aria-label={formatCalendarDay(day, "complete")}
                    aria-current={day === today ? "date" : undefined}
                    onKeyDown={onKey}
                    onClick={() => onPick(day)}
                    className={`size-9 cursor-pointer rounded-full text-body tabular-nums disabled:cursor-not-allowed disabled:bg-transparent disabled:font-normal disabled:text-quaternary ${dayTone(day === selected, day === today)}`}
                  >
                    {Number(day.slice(DAY_OF_MONTH))}
                  </button>
                </td>
              ) : (
                <td key={`blank-${column}`} className="p-0.5" />
              ),
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
