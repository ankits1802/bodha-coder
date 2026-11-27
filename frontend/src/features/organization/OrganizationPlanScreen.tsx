"use client";

import { useMemo } from "react";
import { PlanChooser } from "@/components/shared/plan-chooser/PlanChooser";
import { PLAN_CHOOSER_TEXT } from "@/components/shared/plan-chooser/strings";
import { useCheckoutReturn } from "@/components/shared/plan-chooser/useCheckoutReturn";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlanCatalog } from "@/hooks/usePlanCatalog";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useSession } from "@/lib/session/useSession";
import { organizationBilling } from "./organizationBilling";
import { OrganizationPlanSummary } from "./OrganizationPlanSummary";
import { ORGANIZATION_TEXT } from "./strings";
import { UsageTable } from "./UsageTable";
import { useOrganizationPlan } from "./useOrganizationData";

const words = ORGANIZATION_TEXT.plan;
const TEXT = { loading: words.loading, empty: words.loading, retry: ORGANIZATION_TEXT.retry };

export function OrganizationPlanScreen({ organizationId }: { organizationId: string }) {
  const status = useOrganizationPlan(organizationId);
  const catalog = usePlanCatalog();
  const checkout = useQueryParams().get("checkout");
  const billingOnly = useSession().user?.billing_only === true;
  const actions = useMemo(() => organizationBilling(organizationId), [organizationId]);
  useCheckoutReturn({ done: checkout === "done", billingOnly, reload: status.reload });

  return (
    <>
      <PageHeader title={words.title} />
      {checkout === "done" ? <InlineAlert tone="ok">{PLAN_CHOOSER_TEXT.checkout.done}</InlineAlert> : null}
      {checkout === "cancelled" ? <InlineAlert tone="warn">{PLAN_CHOOSER_TEXT.checkout.cancelled}</InlineAlert> : null}
      <RemoteView state={status.state} text={TEXT} onRetry={status.reload}>
        {(current) => (
          <>
            {current.standing === "ended" ? <InlineAlert tone="warn">{words.ended}</InlineAlert> : null}
            <OrganizationPlanSummary plan={current} />
            <Panel aria-label={words.usageLabel}>
              <UsageTable practices={current.practices} />
            </Panel>
            <RemoteView state={catalog.state} text={TEXT} onRetry={catalog.reload}>
              {(plans) => <PlanChooser status={current} catalog={plans} actions={actions} onChanged={status.reload} />}
            </RemoteView>
          </>
        )}
      </RemoteView>
    </>
  );
}
