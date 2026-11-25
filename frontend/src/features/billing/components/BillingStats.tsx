import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { BillingRow } from "@/lib/api/types";
import { formatCount, formatPercent, ratio } from "@/lib/format";
import { summarise } from "../billingRows";
import { BILLING_TEXT } from "../strings";

export function BillingStats({ rows }: { rows: BillingRow[] }) {
  const summary = summarise(rows);
  return (
    <StatGrid label={BILLING_TEXT.statsLabel}>
      <StatCell label={BILLING_TEXT.visits} value={formatCount(summary.visits)} />
      <StatCell label={BILLING_TEXT.changedInReview} value={formatPercent(ratio(summary.changed, summary.visits))} />
      <StatCell label={BILLING_TEXT.asBilledCount} value={formatCount(summary.asBilled)} />
    </StatGrid>
  );
}
