import type { BillingActions } from "@/components/shared/plan-chooser/billingActions";
import { cancelSubscription, openBillingPortal, startCheckout } from "@/lib/api/plan";

export const PRACTICE_BILLING: BillingActions = {
  checkout: (body) => startCheckout(body),
  portal: () => openBillingPortal(),
  cancel: () => cancelSubscription(),
};
