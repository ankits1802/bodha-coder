import { PLAN_CARD_TEXT } from "@/components/shared/plan-cards/strings";
import { dateFact, standingView } from "@/components/shared/plan-chooser/chooserModel";
import { PLAN_CHOOSER_TEXT } from "@/components/shared/plan-chooser/strings";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { StatusDot } from "@/components/ui/StatusDot";
import type { OrganizationPlan } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/labels";
import { ORGANIZATION_TEXT } from "./strings";

export function OrganizationPlanSummary({ plan }: { plan: OrganizationPlan }) {
  const facts = PLAN_CHOOSER_TEXT.facts;
  const standing = standingView(plan.standing);
  const date = dateFact(plan);
  const subscription = plan.subscription;
  return (
    <StatGrid label={ORGANIZATION_TEXT.plan.summaryLabel}>
      <StatCell label={facts.plan} value={PLAN_LABELS[plan.plan]} note={<StatusDot tone={standing.tone}>{standing.label}</StatusDot>} />
      {date ? <StatCell label={date.label} value={date.value} /> : null}
      <StatCell label={facts.providers} value={formatCount(plan.providers)} />
      <StatCell
        label={facts.payment}
        value={subscription ? PLAN_CHOOSER_TEXT.paidBy[subscription.provider] : FORMAT_WORDS.empty}
        note={subscription ? PLAN_CARD_TEXT.intervals[subscription.interval] : undefined}
      />
    </StatGrid>
  );
}
