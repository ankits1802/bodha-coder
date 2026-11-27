"use client";

import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlanCatalog } from "@/hooks/usePlanCatalog";
import { usePlanStatus } from "@/hooks/usePlanStatus";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useSession } from "@/lib/session/useSession";
import { BilledByOrganization } from "./BilledByOrganization";
import { PlanChooser } from "./PlanChooser";
import { PlanSummary } from "./PlanSummary";
import { PLAN_TEXT } from "./strings";
import { useCheckoutReturn } from "./useCheckoutReturn";

const TEXT = { loading: PLAN_TEXT.loading, empty: PLAN_TEXT.loading, retry: PLAN_TEXT.retry };

export function PlanScreen() {
  const status = usePlanStatus();
  const catalog = usePlanCatalog();
  const checkout = useQueryParams().get("checkout");
  const billingOnly = useSession().user?.billing_only === true;
  useCheckoutReturn({ done: checkout === "done", billingOnly, reload: status.reload });

  return (
    <>
      <PageHeader title={PLAN_TEXT.title} />
      {billingOnly ? <InlineAlert tone="warn">{PLAN_TEXT.ended}</InlineAlert> : null}
      {checkout === "done" ? <InlineAlert tone="ok">{PLAN_TEXT.checkout.done}</InlineAlert> : null}
      {checkout === "cancelled" ? <InlineAlert tone="warn">{PLAN_TEXT.checkout.cancelled}</InlineAlert> : null}
      <RemoteView state={status.state} text={TEXT} onRetry={status.reload}>
        {(current) => (
          <>
            <PlanSummary status={current} />
            {current.organization ? (
              <BilledByOrganization organization={current.organization} />
            ) : (
              <RemoteView state={catalog.state} text={TEXT} onRetry={catalog.reload}>
                {(plans) => <PlanChooser status={current} catalog={plans} onChanged={status.reload} />}
              </RemoteView>
            )}
          </>
        )}
      </RemoteView>
    </>
  );
}
