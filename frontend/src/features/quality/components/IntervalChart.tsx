import { formatRate } from "@/components/shared/rates";
import { FORMAT_WORDS, formatPercent } from "@/lib/format";
import type { RateRow } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

const TICKS = [0, 0.5, 1];

function position(share: number): string {
  return `${share * 100}%`;
}

function Legend() {
  return (
    <span className="flex gap-4 text-footnote text-secondary">
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2.5 rounded-full bg-chart-bar" />
        {QUALITY_TEXT.legend.point}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="h-1.5 w-4 rounded-full bg-chart-muted" />
        {QUALITY_TEXT.legend.interval}
      </span>
    </span>
  );
}

function percentOrDash(share: number | null): string {
  return share === null ? FORMAT_WORDS.empty : formatPercent(share);
}

function rowLabel(row: RateRow): string {
  const { value, low, high } = row.rate;
  return QUALITY_TEXT.chartRow(QUALITY_TEXT.elements[row.key], percentOrDash(value), percentOrDash(low), percentOrDash(high));
}

function Track({ row }: { row: RateRow }) {
  const { value, low, high } = row.rate;
  return (
    <div aria-hidden="true" title={`${QUALITY_TEXT.elements[row.key]} · ${formatRate(row.rate)}`} className="relative h-5">
      <div className="absolute inset-x-0 top-1/2 h-px bg-separator" />
      {low !== null && high !== null ? (
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-chart-muted"
          style={{ left: position(low), width: position(high - low) }}
        />
      ) : null}
      {value !== null ? (
        <div
          className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-chart-bar ring-2 ring-surface"
          style={{ left: position(value) }}
        />
      ) : null}
    </div>
  );
}

export function IntervalChart({ rows, label }: { rows: RateRow[]; label: string }) {
  return (
    <figure className="m-0 flex flex-col gap-3">
      <figcaption className="flex justify-end">
        <Legend />
      </figcaption>
      <ul aria-label={label} className="m-0 flex list-none flex-col gap-2.5 p-0">
        {rows.map((row) => (
          <li key={row.key} aria-label={rowLabel(row)} className="grid grid-cols-[8.5rem_minmax(0,1fr)] items-center gap-x-3 sm:grid-cols-[9.5rem_minmax(0,1fr)_10rem]">
            <span className="text-subhead text-label">{QUALITY_TEXT.elements[row.key]}</span>
            <Track row={row} />
            <span className="col-start-2 text-subhead text-secondary tabular-nums sm:col-start-auto sm:text-right">
              {formatRate(row.rate)}
            </span>
          </li>
        ))}
      </ul>
      <div aria-hidden="true" className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-x-3 sm:grid-cols-[9.5rem_minmax(0,1fr)_10rem]">
        <span />
        <span className="relative h-4 text-micro text-tertiary tabular-nums">
          {TICKS.map((tick) => (
            <span key={tick} className="absolute -translate-x-1/2 first:translate-x-0 last:-translate-x-full" style={{ left: position(tick) }}>
              {formatPercent(tick)}
            </span>
          ))}
        </span>
      </div>
    </figure>
  );
}
