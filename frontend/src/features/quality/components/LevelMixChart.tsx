import { FORMAT_WORDS, formatPercent } from "@/lib/format";
import type { LevelShare } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

function percent(share: number | null): string {
  return share === null ? FORMAT_WORDS.empty : formatPercent(share);
}

function Bar({ share, tone, title }: { share: number | null; tone: string; title: string }) {
  return (
    <div title={title} className="flex h-2.5 items-center">
      <div className={`h-full rounded-r ${tone}`} style={{ width: `${(share ?? 0) * 100}%` }} />
    </div>
  );
}

function Legend() {
  return (
    <span className="flex gap-4 text-footnote text-secondary">
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2.5 rounded-sm bg-chart-bar" />
        {QUALITY_TEXT.mixWindows.recent}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2.5 rounded-sm bg-chart-muted" />
        {QUALITY_TEXT.mixWindows.prior}
      </span>
    </span>
  );
}

export function LevelMixChart({ shares }: { shares: LevelShare[] }) {
  const windows = QUALITY_TEXT.mixWindows;
  return (
    <figure className="m-0 flex flex-col gap-3">
      <figcaption className="flex justify-end">
        <Legend />
      </figcaption>
      <ul aria-label={QUALITY_TEXT.mixLabel} className="m-0 flex list-none flex-col gap-3 p-0">
        {shares.map((row) => (
          <li
            key={row.level}
            aria-label={QUALITY_TEXT.mixRow(row.level, percent(row.recentShare), percent(row.priorShare))}
            className="grid grid-cols-[7.5rem_minmax(0,1fr)_7rem] items-center gap-x-3"
          >
            <span className="text-subhead text-label">{row.level}</span>
            <div aria-hidden="true" className="flex flex-col gap-0.5">
              <Bar share={row.recentShare} tone="bg-chart-bar" title={`${windows.recent} · ${percent(row.recentShare)}`} />
              <Bar share={row.priorShare} tone="bg-chart-muted" title={`${windows.prior} · ${percent(row.priorShare)}`} />
            </div>
            <span aria-hidden="true" className="text-right text-footnote text-secondary tabular-nums">
              {QUALITY_TEXT.mixValues(percent(row.recentShare), percent(row.priorShare))}
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
