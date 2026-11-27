import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { HqExpenditure } from "@/lib/api/types";
import { formatCount, formatMoney, formatUnitCost } from "@/lib/format";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.spend;

export function SpendStats({ report }: { report: HqExpenditure }) {
  const { totals } = report;
  const unpriced = totals.unpriced_analyses > 0 ? words.unpriced(totals.unpriced_analyses, report.unpriced_models) : undefined;
  return (
    <StatGrid label={words.totalsLabel}>
      <StatCell label={words.stats.cost} value={formatMoney(totals.cost_usd)} note={unpriced} />
      <StatCell label={words.stats.costPerNote} value={formatUnitCost(totals.cost_per_note_usd)} />
      <StatCell label={words.stats.notes} value={formatCount(totals.notes)} />
      <StatCell label={words.stats.analyses} value={formatCount(totals.analyses)} />
      <StatCell label={words.stats.inputTokens} value={formatCount(totals.input_tokens)} />
      <StatCell label={words.stats.outputTokens} value={formatCount(totals.output_tokens)} />
    </StatGrid>
  );
}
