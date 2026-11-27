"use client";

import { useEffect } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlanCatalog } from "@/hooks/usePlanCatalog";
import { usePlanStatus } from "@/hooks/usePlanStatus";
import { useQueryParams } from "@/hooks/useQueryParams";
import { PlanChooser } from "./PlanChooser";
import { PlanSummary } from "./PlanSummary";
import { PLAN_TEXT } from "./strings";

const WEBHOOK_WAIT_MS = 4000;
const TEXT = { loading: PLAN_TEXT.loading, empty: PLAN_TEXT.loading, retry: PLAN_TEXT.retry };

export function PlanScreen() {
  const status = usePlanStatus();
  const catalog = usePlanCatalog();
  const checkout = useQueryParams().get("checkout");
  const reload = status.reload;

  useEffect(() => {
    if (checkout !== "done") return;
    const timer = window.setTimeout(reload, WEBHOOK_WAIT_MS);
    return () => window.clearTimeout(timer);
  }, [checkout, reload]);

  return (
    <>
      <PageHeader title={PLAN_TEXT.title} />
      {checkout === "done" ? <InlineAlert tone="ok">{PLAN_TEXT.checkout.done}</InlineAlert> : null}
      {checkout === "cancelled" ? <InlineAlert tone="warn">{PLAN_TEXT.checkout.cancelled}</InlineAlert> : null}
      <RemoteView state={status.state} text={TEXT} onRetry={status.reload}>
        {(current) => (
          <>
            <PlanSummary status={current} />
            <RemoteView state={catalog.state} text={TEXT} onRetry={catalog.reload}>
              {(plans) => <PlanChooser status={current} catalog={plans} onChanged={status.reload} />}
            </RemoteView>
          </>
        )}
      </RemoteView>
    </>
  );
}
