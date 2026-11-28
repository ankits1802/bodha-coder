import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { BillingList } from "@/lib/api/types";
import { formatCount, formatPercent, ratio } from "@/lib/format";
import { billingPath, summarise } from "../billingRows";
import { BILLING_TEXT } from "../strings";

export function BillingStats({ billing, linked }: { billing: BillingList; linked: boolean }) {
  const listed = summarise(billing.items);
  return (
    <StatGrid label={BILLING_TEXT.statsLabel}>
      <StatCell label={BILLING_TEXT.readyToBill} value={formatCount(billing.summary.ready)} href={linked ? billingPath("ready") : null} />
      <StatCell
        label={BILLING_TEXT.exportedToday}
        value={formatCount(billing.summary.exported_today)}
        href={linked ? billingPath("today") : null}
      />
      <StatCell label={BILLING_TEXT.heldForProvider} value={formatCount(billing.summary.held_for_provider)} />
      <StatCell label={BILLING_TEXT.changedInReview} value={formatPercent(ratio(listed.changed, listed.visits))} />
    </StatGrid>
  );
}
