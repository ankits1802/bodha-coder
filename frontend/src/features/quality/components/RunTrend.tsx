import type { EvalRunView } from "@/lib/api/types";
import { formatInstantDay, formatPercent } from "@/lib/format";
import { TREND_RUNS } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

interface TrendPoint {
  id: string;
  day: string;
  share: number;
  prompt: string;
}

function points(runs: EvalRunView[]): TrendPoint[] {
  return runs
    .filter((run) => run.status === "done" && typeof run.summary.em?.value === "number")
    .slice(0, TREND_RUNS)
    .reverse()
    .map((run) => ({
      id: run.id,
      day: run.requested_at ? formatInstantDay(run.requested_at) : "",
      share: run.summary.em?.value ?? 0,
      prompt: run.prompt_version,
    }));
}

function summary(trend: TrendPoint[]): string {
  return QUALITY_TEXT.trendSummary(trend.map((point) => `${point.day} ${formatPercent(point.share)}`).join(", "));
}

export function RunTrend({ runs }: { runs: EvalRunView[] }) {
  const trend = points(runs);
  if (trend.length === 0) return null;
  return (
    <figure className="m-0 flex flex-col gap-2 px-4 pb-4">
      <figcaption className="text-subhead font-medium text-label">{QUALITY_TEXT.trendTitle}</figcaption>
      <div role="img" aria-label={summary(trend)} className="flex h-36 items-end gap-2 border-b border-chart-muted">
        {trend.map((point) => (
          <div key={point.id} className="flex h-full min-w-0 flex-1 flex-col items-center gap-1">
            <span aria-hidden="true" className="text-micro text-secondary tabular-nums">
              {formatPercent(point.share)}
            </span>
            <div className="relative w-full flex-1">
              <div
                title={QUALITY_TEXT.trendBar(point.day, point.prompt, formatPercent(point.share))}
                className="absolute inset-x-0 bottom-0 mx-auto max-w-10 rounded-t bg-chart-bar hover:bg-chart-bar-hover"
                style={{ height: `${Math.max(point.share * 100, 1)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <div aria-hidden="true" className="flex gap-2 text-micro text-tertiary tabular-nums">
        {trend.map((point) => (
          <span key={point.id} className="min-w-0 flex-1 truncate text-center">
            {point.day}
          </span>
        ))}
      </div>
    </figure>
  );
}
