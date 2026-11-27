import { StatusDot } from "@/components/ui/StatusDot";
import type { EmMixFamily, EmMixLevel } from "@/lib/api/types";
import { formatCount, formatPercent } from "@/lib/format";
import { barWidth, benchmarkShare, familyStatus, formatPoints, testLine } from "./emMixFacts";
import { EM_MIX_TEXT } from "./strings";

export const PROVIDER_SWATCH = "bg-chart-bar";
export const CMS_SWATCH = "bg-tertiary";

function LevelRow({ level }: { level: EmMixLevel }) {
  const share = formatPercent(level.share);
  const cms = benchmarkShare(level);
  return (
    <li className="grid grid-cols-[3.25rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1">
      <span className="text-subhead font-medium tabular-nums">{level.code}</span>
      <span aria-hidden="true" title={EM_MIX_TEXT.levelTitle(level.code, share, cms)} className="flex flex-col gap-0.5">
        <span className="h-2 rounded-r bg-chart-grid">
          <span className={`block h-2 rounded-r ${PROVIDER_SWATCH}`} style={{ width: barWidth(level.share) }} />
        </span>
        <span className="h-2 rounded-r bg-chart-grid">
          <span className={`block h-2 rounded-r ${CMS_SWATCH}`} style={{ width: barWidth(level.benchmark) }} />
        </span>
      </span>
      <span className="flex items-center gap-2 text-subhead whitespace-nowrap tabular-nums">
        <span>{EM_MIX_TEXT.levelValues(share, cms)}</span>
        {level.direction ? <StatusDot tone="warn">{formatPoints(level.points)}</StatusDot> : null}
      </span>
    </li>
  );
}

export function FamilyChart({ family }: { family: EmMixFamily }) {
  const status = familyStatus(family);
  const test = testLine(family);
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-field bg-muted-panel px-4 py-3.5">
      <header className="flex flex-col gap-1">
        <h4 className="m-0 font-sans text-callout font-semibold">{family.label}</h4>
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-subhead text-secondary">
          <span className="tabular-nums">{EM_MIX_TEXT.visits(formatCount(family.visits), family.visits)}</span>
          <StatusDot tone={status.tone}>{status.label}</StatusDot>
        </span>
      </header>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {family.levels.map((level) => (
          <LevelRow key={level.code} level={level} />
        ))}
      </ul>
      {test ? <span className="text-footnote text-secondary tabular-nums">{test}</span> : null}
    </article>
  );
}
