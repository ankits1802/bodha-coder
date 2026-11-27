import { PLAN_CARD_TEXT } from "@/components/shared/plan-cards/strings";
import { dateFact, standingView } from "@/components/shared/plan-chooser/chooserModel";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { StatusDot } from "@/components/ui/StatusDot";
import type { PlanStatus } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/labels";
import { PLAN_TEXT } from "./strings";

export function PlanSummary({ status }: { status: PlanStatus }) {
  const words = PLAN_TEXT;
  const standing = standingView(status.standing);
  const date = dateFact(status);
  const subscription = status.subscription;
  const daysLeft = status.trial_days_left !== null ? words.daysLeft(status.trial_days_left) : undefined;
  return (
    <StatGrid label={words.summaryLabel}>
      <StatCell
        label={words.facts.plan}
        value={PLAN_LABELS[status.plan]}
        note={<StatusDot tone={standing.tone}>{standing.label}</StatusDot>}
      />
      {date ? <StatCell label={date.label} value={date.value} note={status.standing === "trial" ? daysLeft : undefined} /> : null}
      <StatCell label={words.facts.providers} value={words.usage(status.providers, status.provider_limit)} />
      <StatCell label={words.facts.users} value={words.usage(status.users, status.user_limit)} />
      <StatCell
        label={words.facts.payment}
        value={subscription ? words.paidBy[subscription.provider] : FORMAT_WORDS.empty}
        note={subscription ? PLAN_CARD_TEXT.intervals[subscription.interval] : undefined}
      />
    </StatGrid>
  );
}
