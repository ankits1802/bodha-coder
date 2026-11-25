import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import type { Outcomes } from "@/lib/api/types";
import { formatPercent, ratio } from "@/lib/format";
import { OUTCOME_ORDER, outcomeTotal, type OutcomeKey } from "../insightMath";
import { INSIGHTS_TEXT } from "../strings";

const SWATCHES: Record<OutcomeKey, string> = {
  matched: "bg-chart-ok",
  billed_too_low: "bg-chart-low",
  diagnosis_changes: "bg-chart-warn",
  billed_too_high: "bg-chart-bad",
};

interface Part {
  key: OutcomeKey;
  label: string;
  value: number;
  share: string;
}

function partsOf(outcomes: Outcomes): Part[] {
  const total = outcomeTotal(outcomes);
  return OUTCOME_ORDER.map((key) => ({
    key,
    label: INSIGHTS_TEXT.outcomes[key],
    value: outcomes[key],
    share: formatPercent(ratio(outcomes[key], total)),
  }));
}

export function OutcomeBar({ outcomes }: { outcomes: Outcomes }) {
  const parts = partsOf(outcomes);
  const shown = parts.filter((part) => part.value > 0);
  const summary = parts.map((part) => INSIGHTS_TEXT.outcomeShare(part.label, part.share)).join(", ");
  return (
    <Panel className="flex flex-col gap-3.5 px-5.5 py-5">
      <h2 className="m-0 font-sans text-headline font-semibold tracking-headline">{INSIGHTS_TEXT.outcomesTitle}</h2>
      {shown.length === 0 ? (
        <EmptyState title={INSIGHTS_TEXT.noOutcomes} />
      ) : (
        <>
          <div role="img" aria-label={summary} className="flex h-3.5 gap-0.5 overflow-hidden rounded">
            {shown.map((part) => (
              <div
                key={part.key}
                title={INSIGHTS_TEXT.partTitle(part.label, part.share)}
                className={SWATCHES[part.key]}
                style={{ flex: `${part.value} 1 0` }}
              />
            ))}
          </div>
          <ul className="m-0 flex list-none flex-wrap gap-x-7 gap-y-2 p-0 text-subhead">
            {parts.map((part) => (
              <li key={part.key} className="inline-flex items-center gap-1.5">
                <span aria-hidden="true" className={`size-2.5 rounded-sm ${SWATCHES[part.key]}`} />
                {part.label}
                <strong className="font-semibold tabular-nums">{part.share}</strong>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
