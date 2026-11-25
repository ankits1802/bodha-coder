import { Panel } from "@/components/ui/Panel";
import { formatCalendarDay, formatCount } from "@/lib/format";
import { axisMax, axisTicks, type DayBar } from "../insightMath";
import { INSIGHTS_TEXT } from "../strings";

const LABEL_EVERY_LIMIT = 31;
const LABEL_EVERY = 7;

function Legend() {
  return (
    <span className="flex gap-4 text-footnote text-secondary">
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2.5 rounded-sm bg-chart-bar" />
        {INSIGHTS_TEXT.weekday}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2.5 rounded-sm bg-chart-muted" />
        {INSIGHTS_TEXT.weekend}
      </span>
    </span>
  );
}

function summary(bars: DayBar[]): string {
  const values = bars.map((bar) => bar.notes);
  const first = bars[0]?.date ?? "";
  const last = bars[bars.length - 1]?.date ?? "";
  return INSIGHTS_TEXT.perDaySummary(
    formatCalendarDay(first),
    formatCalendarDay(last),
    formatCount(Math.min(...values)),
    formatCount(Math.max(...values)),
  );
}

function dayLabel(bar: DayBar, index: number, total: number): string {
  if (total > LABEL_EVERY_LIMIT && index % LABEL_EVERY !== 0) return "";
  return String(Number(bar.date.slice(8)));
}

export function DailyBars({ bars }: { bars: DayBar[] }) {
  const max = axisMax(bars.map((bar) => bar.notes));
  const gap = bars.length > LABEL_EVERY_LIMIT ? "gap-px" : "gap-2";
  return (
    <Panel className="flex flex-col gap-4 px-5.5 py-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="m-0 font-sans text-headline font-semibold tracking-headline">{INSIGHTS_TEXT.perDayTitle}</h2>
        <Legend />
      </div>
      <div className="flex gap-2.5">
        <div aria-hidden="true" className="flex h-55 flex-col justify-between text-right text-micro text-tertiary tabular-nums">
          {axisTicks(max).map((tick) => (
            <span key={tick}>{formatCount(Math.round(tick))}</span>
          ))}
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div role="img" aria-label={summary(bars)} className={`flex h-55 items-end border-b border-chart-muted ${gap}`}>
            {bars.map((bar) => (
              <div
                key={bar.date}
                title={INSIGHTS_TEXT.barTitle(formatCalendarDay(bar.date, "long"), formatCount(bar.notes))}
                className={`min-w-0 flex-1 rounded-t hover:bg-chart-bar-hover ${bar.weekend ? "bg-chart-muted" : "bg-chart-bar"}`}
                style={{ height: `${(bar.notes / max) * 100}%` }}
              />
            ))}
          </div>
          <div aria-hidden="true" className={`flex text-micro text-tertiary tabular-nums ${gap}`}>
            {bars.map((bar, index) => (
              <span key={bar.date} className="min-w-0 flex-1 text-center">
                {dayLabel(bar, index, bars.length)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
