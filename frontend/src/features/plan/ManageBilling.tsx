"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import type { ButtonVariant } from "@/components/ui/buttonStyles";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { cancelSubscription, openBillingPortal } from "@/lib/api/plan";
import type { PlanSubscription } from "@/lib/api/types";
import { leaveFor } from "./leaveFor";
import { PLAN_TEXT } from "./strings";

interface ManageBillingProps {
  subscription: PlanSubscription;
  onChanged: () => void;
}

const words = PLAN_TEXT;

function PortalButton({ variant }: { variant: ButtonVariant }) {
  const portal = useAction(async () => leaveFor((await openBillingPortal()).url));
  return (
    <div className="flex flex-col items-start gap-3">
      <Button variant={variant} pending={portal.pending} onClick={() => void portal.run()}>
        {words.manage}
      </Button>
      {portal.error ? <InlineAlert tone="bad">{portal.error}</InlineAlert> : null}
    </div>
  );
}

function CancelButton({ subscription, onChanged }: ManageBillingProps) {
  const cancel = useAction(cancelSubscription);
  const [confirming, setConfirming] = useState(false);
  const [requested, setRequested] = useState(false);

  async function confirm(): Promise<void> {
    if (!(await cancel.run()).ok) return;
    setConfirming(false);
    setRequested(true);
    onChanged();
  }

  return (
    <div className="flex flex-col items-start gap-3">
      {requested ? <InlineAlert tone="ok">{words.cancel.requested}</InlineAlert> : null}
      <Button variant="danger" disabled={requested || subscription.cancel_at_period_end} onClick={() => setConfirming(true)}>
        {words.cancel.button}
      </Button>
      <ConfirmDialog
        open={confirming}
        title={words.cancel.title}
        confirmLabel={words.cancel.confirm}
        cancelLabel={words.cancel.keep}
        destructive
        pending={cancel.pending}
        error={cancel.error}
        onConfirm={() => void confirm()}
        onClose={() => setConfirming(false)}
      />
    </div>
  );
}

export function ManageBilling({ subscription, onChanged }: ManageBillingProps) {
  if (subscription.managed_by === "portal") return <PortalButton variant="primary" />;
  return (
    <div className="flex flex-wrap items-start gap-3">
      <PortalButton variant="secondary" />
      <CancelButton subscription={subscription} onChanged={onChanged} />
    </div>
  );
}
