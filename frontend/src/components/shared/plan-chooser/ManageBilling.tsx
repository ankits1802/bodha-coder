"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import type { ButtonVariant } from "@/components/ui/buttonStyles";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import type { PlanSubscription } from "@/lib/api/types";
import type { BillingActions } from "./billingActions";
import { leaveFor } from "./leaveFor";
import { PLAN_CHOOSER_TEXT } from "./strings";

interface ManageBillingProps {
  subscription: PlanSubscription;
  actions: BillingActions;
  onChanged: () => void;
}

const words = PLAN_CHOOSER_TEXT;

function PortalButton({ variant, actions }: { variant: ButtonVariant; actions: BillingActions }) {
  const portal = useAction(async () => leaveFor((await actions.portal()).url));
  return (
    <div className="flex flex-col items-start gap-3">
      <Button variant={variant} pending={portal.pending} onClick={() => void portal.run()}>
        {words.manage}
      </Button>
      {portal.error ? <InlineAlert tone="bad">{portal.error}</InlineAlert> : null}
    </div>
  );
}

function CancelButton({ subscription, actions, onChanged }: ManageBillingProps) {
  const cancel = useAction(actions.cancel);
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

export function ManageBilling({ subscription, actions, onChanged }: ManageBillingProps) {
  if (subscription.managed_by === "portal") return <PortalButton variant="primary" actions={actions} />;
  return (
    <div className="flex flex-wrap items-start gap-3">
      <PortalButton variant="secondary" actions={actions} />
      <CancelButton subscription={subscription} actions={actions} onChanged={onChanged} />
    </div>
  );
}
