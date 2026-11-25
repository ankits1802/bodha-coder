import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { BillingList } from "@/lib/api/types";
import { formatCount, formatPercent, ratio } from "@/lib/format";
import { summarise } from "../billingRows";
import { BILLING_TEXT } from "../strings";

export function BillingStats({ billing }: { billing: BillingList }) {
  const listed = summarise(billing.items);
  return (
    <StatGrid label={BILLING_TEXT.statsLabel}>
      <StatCell label={BILLING_TEXT.readyToBill} value={formatCount(billing.summary.ready)} />
      <StatCell label={BILLING_TEXT.exportedToday} value={formatCount(billing.summary.exported_today)} />
      <StatCell label={BILLING_TEXT.heldForProvider} value={formatCount(billing.summary.held_for_provider)} />
      <StatCell label={BILLING_TEXT.changedInReview} value={formatPercent(ratio(listed.changed, listed.visits))} />
    </StatGrid>
  );
}
