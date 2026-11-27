import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { Insights } from "@/lib/api/types";
import { formatCount, formatMoneyChange, formatPercent, ratio } from "@/lib/format";
import { notesRead, outcomeTotal } from "../insightMath";
import { INSIGHTS_TEXT } from "../strings";

export function InsightStats({ insights }: { insights: Insights }) {
  const read = notesRead(insights);
  const total = outcomeTotal(insights.outcomes);
  const matched = ratio(insights.outcomes.matched, total);
  const changed = ratio(total - insights.outcomes.matched, total);
  return (
    <StatGrid label={INSIGHTS_TEXT.statsLabel}>
      <StatCell
        label={INSIGHTS_TEXT.notesRead}
        value={formatCount(read)}
        note={INSIGHTS_TEXT.perDay(formatCount(Math.round(read / insights.days)))}
      />
      <StatCell
        label={INSIGHTS_TEXT.onTime}
        value={formatPercent(ratio(insights.approved_on_time, insights.approved))}
        note={INSIGHTS_TEXT.approvedCount(formatCount(insights.approved))}
      />
      <StatCell
        label={INSIGHTS_TEXT.matched}
        value={formatPercent(matched)}
        note={changed === null ? undefined : INSIGHTS_TEXT.changedShare(formatPercent(changed))}
      />
      <StatCell
        label={INSIGHTS_TEXT.estimate}
        value={formatMoneyChange(insights.estimates.notes > 0 ? insights.estimates.difference : null)}
        note={INSIGHTS_TEXT.estimateNotes(formatCount(insights.estimates.notes))}
      />
    </StatGrid>
  );
}
